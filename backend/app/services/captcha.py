"""Server-side CAPTCHA for the student and counselor logins.

Before this, the verification code was drawn and compared entirely in the
browser, so the server never checked it and a script could skip it by calling
the login endpoint directly. Now the server owns the whole exchange:

  GET  /api/auth/captcha  -> {token, image}   (image is a PNG data URI)
  POST /api/auth/login | /counselor-login     (must send token + the typed code)

The token is `nonce.expiry.signature`. The signature is an HMAC over the nonce,
expiry and the *correct answer*, keyed with a server secret, so the token
proves what the answer is without revealing it. Each token works once (even a
wrong guess burns it, so one image cannot be brute-forced) and expires after
CAPTCHA_TTL_SECONDS.

State is in memory, like the rest of the auth layer (ACTIVE_TOKENS), so it is
per-process. Set CAPTCHA_SECRET (or AUTH_SECRET) in the environment so tokens
survive a restart; without either, a random secret is generated at startup.
"""
import base64
import hashlib
import hmac
import io
import os
import random
import secrets
import time

from fastapi import HTTPException

CAPTCHA_TTL_SECONDS = 180
CAPTCHA_LENGTH = 6
# No 0/O, 1/I/L lookalikes. Answers are compared case-insensitively.
_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

_SECRET = (
    os.getenv("CAPTCHA_SECRET") or os.getenv("AUTH_SECRET") or secrets.token_hex(32)
).encode()

_USED: dict[str, int] = {}  # nonce -> expiry (kept until it would have expired)


def _sign(nonce: str, exp: int, answer: str) -> str:
    msg = f"{nonce}.{exp}.{answer}".encode()
    return hmac.new(_SECRET, msg, hashlib.sha256).hexdigest()


def _load_font(size: int):
    from PIL import ImageFont

    try:
        return ImageFont.load_default(size=size)  # Pillow >= 10.1, scalable
    except TypeError:
        pass
    for path in (
        "DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _render(text: str) -> bytes:
    from PIL import Image, ImageDraw, ImageFilter

    w, h = 180, 60
    img = Image.new("RGB", (w, h), (249, 250, 251))
    draw = ImageDraw.Draw(img)
    font = _load_font(34)

    for _ in range(7):
        draw.line(
            [(random.randint(0, w), random.randint(0, h)),
             (random.randint(0, w), random.randint(0, h))],
            fill=(random.randint(120, 200), random.randint(120, 200), random.randint(120, 200)),
            width=random.randint(1, 2),
        )

    step = (w - 24) // len(text)
    for i, ch in enumerate(text):
        layer = Image.new("RGBA", (46, 54), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text(
            (8, 6), ch, font=font,
            fill=(random.randint(20, 110), random.randint(0, 50), random.randint(0, 60), 255),
        )
        layer = layer.rotate(random.uniform(-28, 28), resample=Image.BICUBIC, expand=False)
        img.paste(layer, (10 + i * step + random.randint(-2, 2), random.randint(-2, 4)), layer)

    for _ in range(160):
        draw.point((random.randint(0, w - 1), random.randint(0, h - 1)),
                   fill=(random.randint(60, 180),) * 3)
    for _ in range(3):
        y = random.randint(8, h - 8)
        draw.line([(0, y), (w, y + random.randint(-10, 10))],
                  fill=(random.randint(40, 120),) * 3, width=1)

    img = img.filter(ImageFilter.GaussianBlur(0.5))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _sweep(now: float) -> None:
    for nonce in [n for n, exp in _USED.items() if exp < now]:
        del _USED[nonce]


def new_challenge() -> dict:
    """Create a challenge: {"token": str, "image": "data:image/png;base64,..."}."""
    text = "".join(secrets.choice(_CHARS) for _ in range(CAPTCHA_LENGTH))
    try:
        png = _render(text)
    except ImportError:
        raise HTTPException(status_code=503, detail="Verification service unavailable")
    nonce = secrets.token_urlsafe(12)
    exp = int(time.time()) + CAPTCHA_TTL_SECONDS
    return {
        "token": f"{nonce}.{exp}.{_sign(nonce, exp, text)}",
        "image": "data:image/png;base64," + base64.b64encode(png).decode(),
    }


def verify_captcha(token: str, answer: str) -> None:
    """Raise HTTP 400 unless `answer` solves the challenge `token`. Single use."""
    bad = HTTPException(status_code=400, detail="Incorrect or expired verification code. Please try again.")
    now = time.time()
    _sweep(now)

    parts = (token or "").split(".")
    if len(parts) != 3 or not (answer or "").strip():
        raise bad
    nonce, exp_s, sig = parts
    try:
        exp = int(exp_s)
    except ValueError:
        raise bad
    if exp < now or nonce in _USED:
        raise bad

    _USED[nonce] = exp  # burn it before comparing: a wrong guess uses it up too
    expected = _sign(nonce, exp, answer.strip().upper())
    if not hmac.compare_digest(expected, sig):
        raise bad

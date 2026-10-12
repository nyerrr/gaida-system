"""
build_validation_packet_pdf.py
------------------------------
Builds THREE separate printable PDFs, one per dataset in GAIDA that is meant to
be validated by licensed guidance counselors:

  GAIDA_Section_A_Expert_Validation.pdf
      100 real, de-identified pilot messages, blank labels -> inter-expert
      agreement. source: expert_validation/real_expert_sample.csv (built by
      build_real_expert_sample.py). The old synthetic sample_for_experts.csv
      is kept only as the gold-key evaluation set for score_detection.py.

  GAIDA_Section_B_Training_Label_Audit.pdf
      90 real training rows, our current label shown -> label integrity.
      source: expert_validation/training_audit.csv

  GAIDA_Section_C_Voice_Acoustic_Validation.pdf
      Protocol + blank clip-label log for the voice / acoustic scoring.
      source: acoustic_validation/sample_labeled_acoustic.csv (worked examples)

The `gold_key.csv` answer key is deliberately NOT included - it must never
reach the raters.

Usage (from backend/):
    python training/build_validation_packet_pdf.py
    # optional:
    python training/build_validation_packet_pdf.py --out-dir path/to/output
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    LongTable,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject
    _HAVE_PYPDF = True
except Exception:  # pypdf optional; if missing, metadata just isn't scrubbed
    _HAVE_PYPDF = False

BASE = Path(__file__).resolve().parent
EXPERT = BASE / "expert_validation"
ACOUSTIC = BASE / "acoustic_validation"

LABEL_COLS = ["anxiety", "sadness", "neutral", "suicidal", "anger"]
LABEL_DEFS = {
    "anxiety": "nervousness, worry, tension, dread, panic-like feelings, overthinking",
    "sadness": "low mood, grief, loneliness, emptiness, crying",
    "neutral": "casual or everyday statements with no significant distress",
    "suicidal": "death wishes, wanting to end one's life, self-harm - even when phrased indirectly",
    "anger": "irritation, frustration, hostility",
}
LABEL_EXAMPLES = {
    "anxiety": "my heart is racing and I can't calm down",
    "sadness": "I've been crying all day and I can't stop",
    "neutral": "I passed my math exam",
    "suicidal": "I want to kill myself",
    "anger": "I'm so angry my blood is boiling",
}

FOOTER_LEFT = "GAIDA - University of the East - College Guidance"

# ---------------------------------------------------------------- helpers


def clean(text: str) -> str:
    """Normalize to characters the built-in PDF fonts can render."""
    text = (text or "").strip()
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u2026": "...", "\u00a0": " ",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def load_csv(name: Path) -> list[dict]:
    with open(name, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def scrub_metadata(path: Path, title: str) -> None:
    """Clear build-time timestamps and other identifying PDF metadata.

    The confidentiality note promises no timestamps, so the file's own
    /CreationDate, /ModDate and /Producer fields must be cleared too - the
    visible text alone is not enough. No-op if pypdf is not installed.
    """
    if not _HAVE_PYPDF:
        return
    reader = PdfReader(str(path))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({
        "/Title": title, "/Author": "", "/Subject": "",
        "/Creator": "GAIDA validation packet", "/Producer": "", "/Keywords": "",
    })
    for key in ("/CreationDate", "/ModDate"):
        try:
            del writer._info[NameObject(key)]
        except (KeyError, TypeError):
            pass
    tmp = path.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as f:
        writer.write(f)
    tmp.replace(path)


# ---------------------------------------------------------------- styles

ss = getSampleStyleSheet()

TITLE = ParagraphStyle("title", parent=ss["Title"], fontName="Helvetica-Bold",
                       fontSize=19, leading=23, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=ss["Normal"], fontName="Helvetica",
                     fontSize=10.5, leading=14, textColor=colors.HexColor("#555555"),
                     spaceAfter=10)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=13, leading=16, spaceBefore=14, spaceAfter=6,
                    textColor=colors.HexColor("#1a1a1a"))
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica",
                      fontSize=10, leading=14, spaceAfter=6)
CELL = ParagraphStyle("cell", parent=ss["Normal"], fontName="Helvetica",
                      fontSize=8.7, leading=10.5)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
CELLH = ParagraphStyle("cellh", parent=CELL, fontName="Helvetica-Bold")
CTX = ParagraphStyle("ctx", parent=CELL, fontName="Helvetica-Oblique",
                     fontSize=7.2, leading=9, textColor=colors.HexColor("#666666"))
LEGEND = ParagraphStyle("legend", parent=ss["Normal"], fontName="Helvetica",
                        fontSize=9.5, leading=13.5, leftIndent=12,
                        bulletIndent=0, spaceAfter=3)

GREY = colors.HexColor("#eeeeee")
ROW_ALT = colors.HexColor("#f7f7f7")
LINE = colors.HexColor("#bbbbbb")


def p(text, style=CELL):
    return Paragraph(clean(text), style)


# ---------------------------------------------------------------- framing


def _decorate(canvas, doc, section: str):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#777777"))
    canvas.drawString(36, 24, FOOTER_LEFT)
    if section:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawCentredString(letter[0] / 2.0, 24, section)
    canvas.drawRightString(letter[0] - 36, 24, "Page %d" % doc.page)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.4)
    canvas.line(36, 34, letter[0] - 36, 34)
    canvas.restoreState()


class PacketDoc(BaseDocTemplate):
    """Single-section document with a fixed running footer."""

    def __init__(self, filename, section: str):
        BaseDocTemplate.__init__(self, filename, pagesize=letter,
                                 leftMargin=36, rightMargin=36,
                                 topMargin=42, bottomMargin=44)
        frame = Frame(36, 44, letter[0] - 72, letter[1] - 86, id="body")
        self.section = section
        self.addPageTemplates([
            PageTemplate(id="body", frames=[frame],
                         onPage=lambda c, d: _decorate(c, d, self.section)),
        ])


def _title_block(title: str, subtitle: str) -> list:
    return [
        Paragraph(clean(title), TITLE),
        Paragraph(clean(subtitle), SUB),
        Paragraph(
            "AI-based Anxiety Detection System &nbsp;&middot;&nbsp; College Guidance "
            "&nbsp;&middot;&nbsp; University of the East", SUB),
    ]


def _signoff_table(a, b, c, d, extra_label="List name (A or B): ________"):
    t = Table([[clean(a), clean(b)], [clean(c), clean(d)]],
              colWidths=[3.6 * inch, 3.9 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _confidentiality_note() -> Paragraph:
    return Paragraph(
        "<b>Confidentiality.</b> These items are real student messages quoted "
        "verbatim from pilot conversations and have been de-identified - no "
        "names, student IDs, or timestamps appear in this document or in its "
        "file properties. Some reference distress including indirect "
        "self-harm. Responses are compared anonymously for research use only "
        "and must not be photographed, copied, or shared.", BODY)


def _label_definitions_flow(include_examples: bool) -> list:
    flow = [Paragraph("Label Definitions", H2)]
    for key in LABEL_COLS:
        txt = f"<b>{key}</b> - {LABEL_DEFS[key]}"
        if include_examples:
            txt += f'. <i>e.g. "{LABEL_EXAMPLES[key]}"</i>'
        flow.append(Paragraph(txt, LEGEND))
    return flow


def _grid_style(extra=None):
    base = [
        ("BACKGROUND", (0, 0), (-1, 0), GREY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    return base + (extra or [])


# ---------------------------------------------------------------- sections


def section_a_story() -> list:
    real = EXPERT / "real_expert_sample.csv"
    source = real if real.exists() else EXPERT / "sample_for_experts.csv"
    rows = load_csv(source)
    n = len(rows)
    header = [p("#", CELLH), p("What the conversation is about", CELLH),
              p("Student Message (bold = label this)", CELLH)] + \
             [p(c, CELLH) for c in LABEL_COLS]
    data = [header] + [
        [p(r["sample_id"], CELL),
         p(r.get("context_summary") or r.get("context", "") or "", CTX),
         p(r["text"], CELLB)] + [""] * 5 for r in rows
    ]
    widths = [0.34 * inch, 2.45 * inch, 1.51 * inch] + [0.64 * inch] * 5
    t = LongTable(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(_grid_style([
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (-1, -1), "CENTER"),
    ])))
    return (
        _title_block(
            "GAIDA - Expert Validation (Section A)",
            "Rating sheet: label scheme and inter-expert agreement")
        + [
            Paragraph(
                "<b>Purpose.</b> GAIDA sorts each student message into one of five "
                "distress categories using rules plus machine-learned models. Below "
                "are %d real student messages (verbatim, de-identified) collected "
                "during pilot use of the system. We ask a licensed mental health "
                "professional to independently label the sample to confirm the "
                "category scheme is clinically sound and to measure agreement "
                "between raters." % n, BODY),
            Paragraph(
                "<b>How to answer.</b> Label the message shown in <b>bold</b> by "
                "putting a check in the box of the ONE label you judge as the "
                "closest match. The italic column paraphrases <b>what the "
                "conversation is about</b> (from the student's earlier messages in "
                "the same chat) so that short replies such as \"True true\" or "
                "\"4 years\" can be judged in flow. Work from the wording alone; do "
                "not discuss items with the other rater until both sheets are "
                "submitted. If a message stays unclassifiable even with its context "
                "(pure filler), mark it <b>neutral</b>. <b>Time:</b> ~25-40 minutes. "
                "<b>Items:</b> %d." % n, BODY),
            Paragraph(
                "<b>Note on grief and loss.</b> Messages about grief, breakups, or "
                "loss (e.g. death in the family, end of a relationship) belong to "
                "<b>sadness</b> in this five-class scheme. GAIDA routes those "
                "detections to its separate loss/grief protocol - never the anxiety "
                "ladder - after detection, so choosing sadness here is the "
                "clinically correct answer.", BODY),
            _confidentiality_note(),
        ]
        + _label_definitions_flow(include_examples=True)
        + [Spacer(1, 8), t, Spacer(1, 14),
           _signoff_table("Rater name: ______________________________",
                          "Date: ___________________",
                          "Signature: ___________________________________",
                          "List name (A or B): ________")]
    )


def section_b_story() -> list:
    rows = load_csv(EXPERT / "training_audit.csv")
    header = [p("#", CELLH), p("Student Message (from our training data)", CELLH),
              p("Current Label", CELLH), p("Agree", CELLH),
              p("If NOT agree, corrected label", CELLH)]
    data = [header] + [
        [p(r["sample_id"], CELL), p(r["text"], CELL),
         p(r["current_label"], CELLB), "", ""] for r in rows
    ]
    widths = [0.32 * inch, 3.05 * inch, 0.85 * inch, 0.6 * inch, 1.68 * inch]
    t = LongTable(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(_grid_style([
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),
    ])))
    return (
        _title_block(
            "GAIDA - Training Data Label Audit (Section B)",
            "Verifying the annotations the classifier learned from")
        + [
            Paragraph(
                "<b>Purpose.</b> Below are 90 rows that were actually used to train "
                "GAIDA's intent classifier. For each row our current label is shown. "
                "We ask a licensed mental health professional to confirm the label is "
                "clinically correct, or supply the correction. This validates the "
                "dataset itself, not new messages. This is a balanced audit sample "
                "(18 per class, 20% each); it is not the training distribution.", BODY),
            Paragraph(
                "<b>How to answer.</b> Check <b>Agree</b> if our label is correct; if "
                "it is not, write the corrected label in the last column. "
                "<b>Time:</b> ~10-15 minutes. <b>Items:</b> 90.", BODY),
            _confidentiality_note(),
        ]
        + _label_definitions_flow(include_examples=False)
        + [Spacer(1, 8), t, Spacer(1, 14),
           _signoff_table("Rater name: ______________________________",
                          "Date: ___________________",
                          "Signature: ___________________________________",
                          "List name (A or B): ________")]
    )


def section_c_story() -> list:
    examples = load_csv(ACOUSTIC / "sample_labeled_acoustic.csv")
    header = [p("Filename", CELLH), p("Emotion", CELLH),
              p("Severity", CELLH), p("Note", CELLH)]
    example_rows = [[p(r["filename"], CELL), p(r["emotion"], CELL),
                     p(r["severity"], CELL), p(r["note"], CELL)] for r in examples]
    blank_rows = [["", "", "", ""] for _ in range(50)]
    data = [header] + example_rows + blank_rows
    widths = [2.05 * inch, 0.95 * inch, 1.0 * inch, 3.0 * inch]
    t = LongTable(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle(_grid_style([
        ("BACKGROUND", (0, 1), (-1, len(example_rows)), ROW_ALT),
        ("ALIGN", (1, 0), (2, -1), "CENTER"),
    ])))
    return (
        _title_block(
            "GAIDA - Voice / Acoustic Validation (Section C)",
            "Clip labeling log for the voice-scoring pipeline")
        + [
            Paragraph(
                "<b>Purpose.</b> GAIDA's voice pipeline extracts prosody features "
                "(pitch, energy, jitter/shimmer, speech rate, pauses) and maps them to "
                "an emotion and a severity. Its real-world accuracy has never been "
                "measured against human-labeled audio - this log is how it is closed.",
                BODY),
            Paragraph(
                "<b>Status.</b> As of this printing, no labeled audio clips exist "
                "yet (audio_samples/ is empty). This sheet documents the protocol "
                "and the worked-example format only; it becomes a live validation "
                "dataset after clips are collected and labeled.", BODY),
            Paragraph(
                "<b>Protocol.</b> Have consenting volunteers read a small script while "
                "intentionally calm / anxious / sad / angry / neutral - the same words "
                "with different delivery, so the only difference is prosody. A phone "
                "recording is fine. <b>Target:</b> at least 10 clips per emotion (50 "
                "total).", BODY),
            Paragraph(
                "<b>How to label.</b> For each clip, name the file and record the "
                "emotion it genuinely expresses and the distress severity you judge.",
                BODY),
            Paragraph("&bull;&nbsp; <b>Emotion</b> - one of: anxious, sad, angry, "
                      "calm, neutral", LEGEND),
            Paragraph("&bull;&nbsp; <b>Severity</b> - one of: Normal, Low, Moderate, "
                      "High (voice alone can never reach Crisis).", LEGEND),
            Paragraph("&bull;&nbsp; The five shaded rows are worked examples of the "
                      "format.", LEGEND),
            Spacer(1, 8), t, Spacer(1, 14),
            _signoff_table("Rater name: ______________________________",
                           "Date: ___________________",
                           "Signature: ___________________________________",
                           "Clips labeled: ________"),
        ]
    )


# ---------------------------------------------------------------- build

DOCS = [
    ("GAIDA_Section_A_Expert_Validation.pdf",
     "Section A - Expert Validation", section_a_story),
    ("GAIDA_Section_B_Training_Label_Audit.pdf",
     "Section B - Training Data Label Audit", section_b_story),
    ("GAIDA_Section_C_Voice_Acoustic_Validation.pdf",
     "Section C - Voice / Acoustic Validation", section_c_story),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_dir = BASE / "validation_packet"
    parser.add_argument("--out-dir", default=str(default_dir))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for filename, section, story_fn in DOCS:
        path = out_dir / filename
        doc = PacketDoc(str(path), section)
        doc.build(story_fn())
        scrub_metadata(path, section)
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()

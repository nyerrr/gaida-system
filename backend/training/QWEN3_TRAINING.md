# Fine-tune GAIDA and serve it from a provider

This is the end-to-end path from `finetune.jsonl` to production: train a LoRA
adapter on a free GPU, host it behind an OpenAI-compatible API, then point the
Render backend at it without changing application code.

> **OpenAI fine-tuning is being wound down.** As of 2026, OpenAI blocked new
> organisations from creating fine-tuning jobs, and organisations that have not
> run inference on a fine-tuned model in the last 60 days are also blocked. New
> job creation ends for existing customers in January 2027. Existing fine-tuned
> models still serve until their base model is shut down. Do **not** plan a
> defense around creating a new OpenAI fine-tune — it may fail at job creation.
> Use Fireworks (managed training + hosting) or the retrieval path instead.

| | OpenAI (winding down) | Fireworks managed | Open-weight LoRA + host |
|---|---|---|---|
| Training | Paid per token, blocked for inactive orgs | No card, starter credit, ~$0.50/1M tokens | Free on Kaggle/Colab T4 |
| Hosting | Included, per-token | Included | Your provider; free tiers are limited |
| Model | `ft:gpt-4.1-mini:...` | their model ID | Qwen3-4B + your adapter |
| Setup effort | Low, but may not be available | Low | Medium |

The backend supports all three. Keep `LLM_FALLBACK_*` pointed at the free model.
A fine-tune is an enhancement, never a single point of failure.

---

## Path A — OpenAI fine-tune (legacy, may be unavailable)

`training/upload_file.py` creates the job and `training/check_status.py <job-id>`
polls it. **If you already have a working `ft:` model from before the wind-down**,
it still serves until its base model is deprecated, so you can still use it.
Creating a *new* job may now fail with a permissions error.

Once you have a model ID like:

```
ft:gpt-4.1-mini-2025-04-14:your-org:gaida-v2:abc123
```

Set these in the Render dashboard and redeploy:

```
OPENAI_API_KEY=sk-...
LLM_MODEL=ft:gpt-4.1-mini-2025-04-14:your-org:gaida-v2:abc123
# Leave LLM_BASE_URL and HF_TOKEN unset for OpenAI.
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_API_KEY=<your Groq key>
LLM_FALLBACK_MODEL=qwen/qwen3.8-27b
```

No code changes. Check the log line:

```
LLM chat target 'primary' configured: model=ft:gpt-4.1-mini... base_url=https://api.openai.com/v1 (SDK default)
```

Cost warning: every reply is billed at the fine-tuned model's per-token rate,
which is higher than the base model. The fallback only runs when the primary
call *fails*, not when it is merely expensive.

---

## Path B — Qwen3 LoRA on a free Kaggle GPU

Defaults are sized for one 16 GB T4: Qwen3-4B, 4-bit QLoRA, max length 1024,
batch 1 + gradient accumulation. An 8B model or 2048-token sequences need more
VRAM and will OOM on a free T4.

### 1. Prepare the data (any machine)

```bash
pip install -r backend/training/requirements-qwen.txt
python backend/training/prepare_qwen_data.py
```

This writes `backend/training/qwen_data/train.jsonl` and `validation.jsonl`
(90/10 split, seed 42) without modifying `finetune.jsonl`.

Before training, review those files for:

- **Advice in assistant replies.** The runtime prompt forbids advice, but
  several dataset replies give it ("You might remove saved payment details…").
  A fine-tune learns exactly what is in the file, so this will regress the
  no-advice behavior.
- **Crisis replies.** They contain the correct hotlines, but are still worth a
  human read before they become model weights.
- **Duplicates / near-duplicates** between train and validation. They inflate
  validation scores without improving the model.

### 2. Train on Kaggle

1. Create a Kaggle Notebook → **Settings → Accelerator → GPU T4 x2**.
2. Upload this repo (or clone it), then run:

```bash
pip install -r backend/training/requirements-qwen.txt
# Option 1: use the prepared 90/10 split
python backend/training/prepare_qwen_data.py
python backend/training/train_qwen3.py

# Option 2: train straight from the source file (splits 90/10 internally)
python backend/training/train_qwen3.py --data backend/training/finetune.jsonl
```

Useful flags:

| Flag | Default | When to change |
|---|---|---|
| `--model` | `Qwen/Qwen3-4B` | 8B needs ~24 GB; not on a free T4 |
| `--max-length` | `1024` | Lower to 768 if you OOM |
| `--epochs` | `2` | 3 for a stronger fit; watch for overfit |
| `--lora-r` | `16` | Must be ≤32 for Cloudflare Workers AI |
| `--enable-thinking` | off | GAIDA replies are plain text, so leave off |

The script uses fp16 on T4 (no bf16 support), paged AdamW, cosine schedule, and
gradient checkpointing. It also tolerates older TRL versions on Kaggle images by
dropping config fields that version does not know.

Output lands in `backend/training/qwen3-gaida-lora/final/` — this directory is
the adapter plus tokenizer. Download it from the notebook's output panel.

### 3. Check the adapter honestly

```bash
python backend/training/prepare_qwen_data.py
# Compare base vs adapter on your own held-out prompts.
```

`finetune_test.jsonl` currently has **10 examples**. That is too small to claim
the fine-tune is better. Expand it to ~50–100 hand-written, held-out
conversations, and score both models on: language matching (English/Taglish),
one-question-per-reply, no advice, crisis resources, and no exemplar echoing.

### 4. Host the adapter

Your adapter trained on Qwen3-4B must be served by a host that runs Qwen3 and
loads PEFT adapters. OpenRouter, Gemini, and Groq's normal API do **not** accept
custom adapters. Groq's LoRA feature exists but is **enterprise-tier only**.

Cost reality for a zero-budget project (checked November 2026):

| Host | Minimum to start | Notes |
|---|---|---|
| **Fireworks AI** | No card; starter credits | Managed training **and** hosting. Training from $0.50/1M tokens, so this dataset (~132K tokens) is a few cents per epoch. Simplest real fine-tune. |
| **OpenAI** | $5 prepaid minimum | ~$2 for 3 epochs on `gpt-4.1-mini`. Already scripted in this repo. |
| **Together AI** | **$15 minimum credit** | Good product, but the deposit makes it a non-starter here. |
| **Cloudflare Workers AI** | Free | LoRA beta is free, but only Llama 2 7B / Mistral 7B / Gemma family. **Not Qwen3-4B** — you would retrain on a different base. |
| **Hugging Face Endpoints** | Paid plan + card | ~$0.50/hr T4. Free Spaces work but sleep. |
| **Modal** | Free monthly credits | vLLM + adapter; credits run out, endpoint sleeps. |
| **Groq LoRA** | Enterprise contract | Not available to individual/dev accounts. |

If you want the least work and no new account, use **Fireworks** (no card) or
**OpenAI** (if you still have credit from the earlier fine-tune).

#### Option 1 — Fireworks AI (no card, managed train + host)

Fireworks does the training for you, so skip Kaggle entirely:

1. Sign up at https://app.fireworks.ai. New accounts get **$1 in free starter
   credit with no credit card**. Without a card you are capped at 10 requests
   per minute and the account pauses at a $0 balance — fine for a defense demo,
   not for production.
2. **Fine-tuning → New job → upload `backend/training/finetune.jsonl`**
   (OpenAI chat format, which is what it expects).
3. Pick a tunable base model from their list, start the job.
4. **Deploy the LoRA** when the job finishes (serverless if the base supports
   it, otherwise an on-demand deployment).
5. Copy the exact **model ID** the dashboard shows.

Cost: training is billed per token. This dataset is ~132K tokens, so one epoch
is roughly **$0.07** and three epochs ~$0.20 — inside the $1 credit. If you run
out, note that the first top-up minimum may be **$15**, so don't let a demo burn
through the balance.

Promo to check at signup (November 2026): **Muse Glimmer 30B SFT is free to
train until November 30, 2026, no credit card**. If that model fits your data,
training is $0 and the $1 credit is only for inference.

Render env:

```
LLM_API_KEY=<Fireworks API key>
LLM_BASE_URL=https://api.fireworks.ai/inference/v1
LLM_MODEL=accounts/<your-account>/models/<your-model-id>
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_API_KEY=<Groq key>
LLM_FALLBACK_MODEL=qwen/qwen3.8-27b
```

CLI alternative if you already have an adapter from Kaggle:

```bash
pip install firectl
firectl model create <your-model-id> --base-model accounts/fireworks/models/<base>
firectl deployment create <your-model-id> --deployment-shape default
```

See [Import trained models](https://docs.fireworks.ai/models/uploading-custom-models#importing-trained-models)
and [Deploying LoRAs](https://docs.fireworks.ai/fine-tuning/deploying-loras).

#### Option 2 — Together AI (requires $15 minimum credit)

Together accepts externally trained adapters and exposes an OpenAI-compatible
chat endpoint, but the **$15 minimum credit purchase** is why this is not the
default recommendation for a zero-budget project.

Follow [Upload a LoRA adapter](https://docs.together.ai/docs/dedicated-endpoints/adapter):

1. Upload the adapter directory (`.../final/`).
2. Create a dedicated endpoint or use their serverless LoRA path if your base
   model is supported.
3. Copy the **endpoint base URL** and the **model identifier** it returns.

Render env:

```
HF_TOKEN=<Together API key>        # or LLM_API_KEY
LLM_BASE_URL=https://api-inference.together.ai/v1
LLM_MODEL=<the model/endpoint id Together gave you>
```

Together's fine-tuning and inference APIs use different base URLs. The chat
path needs the **inference** URL, not the training one.

#### Option 3 — Cloudflare Workers AI (free, but not for Qwen3)

Workers AI runs LoRA adapters in open beta and is **free during the beta**, with
10,000 Neurons/day on the free plan. However, the supported bases are the
Llama 2 7B, Mistral 7B Instruct v0.2, and Gemma families — **Qwen3-4B is not
supported**. Using this means retraining with `--model mistralai/Mistral-7B-Instruct-v0.2`
(or similar) and accepting an older base model.

- Rank ≤ 32 (your default `--lora-r 16` fits).
- Adapter ≤ 300 MB, file names exactly `adapter_config.json` and
  `adapter_model.safetensors`.
- Add `"model_type": "mistral" | "llama" | "gemma"` to `adapter_config.json`.
- The REST API is not the plain OpenAI chat shape: the adapter is passed as a
  separate `lora` field, so `gpt_agent.py` would need a small adapter layer.

#### Option 4 — Hugging Face

Two different products, often confused:

- **Inference Providers (serverless router)** — pay-as-you-go, cheap, but does
  not serve your arbitrary adapter.
- **Inference Endpoints** — dedicated GPU, supports adapters, requires a paid
  plan and a card on file (~$0.50/hr for a T4). Not free.

A free alternative is a **Space** running vLLM/TGI with your adapter, but free
CPU Spaces are slow and sleep, and ZeroGPU has a daily quota. Acceptable for a
demo if you warm it up before presenting, not for a real pilot.

#### Option 5 — Modal (free monthly credits)

Modal gives free monthly compute credits and is the smoothest way to run vLLM
with LoRA on GPU. You deploy a small vLLM service that loads the base model plus
your adapter and exposes `/v1/chat/completions`. Render then points at the Modal
URL. Credits are finite and the endpoint is not guaranteed up during a defense.

### 5. Point Render at the host

Render dashboard → `gaida-backend` → **Environment**:

```
# Fine-tuned primary
LLM_API_KEY=<provider key>            # or HF_TOKEN
LLM_BASE_URL=<provider OpenAI-compatible /v1 URL>
LLM_MODEL=<adapter model id>

# Free fallback when the host is down / cold / rate-limited
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_API_KEY=<Groq key>
LLM_FALLBACK_MODEL=qwen/qwen3.8-27b

# Keep dataset retrieval on unless you are A/B testing
FINETUNE_FEWSHOT=1
```

`LLM_API_KEY` takes precedence over `HF_TOKEN`, which takes precedence over
`OPENAI_API_KEY`. The fallback reuses the primary key when
`LLM_FALLBACK_API_KEY` is omitted.

Save → **Manual Deploy → Deploy latest commit**. Then check the logs for:

```
LLM chat target 'primary' configured: model=<adapter id> base_url=<host>
LLM chat target 'fallback' configured: model=qwen/qwen3.8-27b base_url=https://api.groq.com/openai/v1
```

If the primary host is down, you will see:

```
LLM target 'primary' failed (<model>): ...; trying next target
```

…and the reply still arrives via Groq. That is the intended behavior.

### 6. Verify from the deployed app

1. Open the Vercel frontend.
2. Send a message that matches a dataset flow ("I failed my midterm…").
3. In Render logs, confirm the primary target answered, not the fallback.
4. Send a crisis message and confirm hotline numbers are still present. Crisis
   is deliberately excluded from dataset few-shot, and the deterministic
   resource check still runs.

---

## Vercel frontend

`frontend/src/config.js` reads `VITE_BACKEND_URL` at **build time**, so changing
it requires a redeploy, not just a save.

Vercel → project → **Settings → Environment Variables**:

```
VITE_BACKEND_URL=https://<your-render-service>.onrender.com
```

Then **Deployments → Redeploy** (uncheck "use existing build cache"). If the
frontend still calls the old host, the variable was added after the build or the
build cache was reused.

CORS already allows `https://gaida-system.vercel.app` in `backend/app/main.py`.
If you use a custom domain, add it there too.

---

## When the fine-tune is worse than what you have

Watch for these, in order of likelihood:

1. **Advice leaks.** The dataset contains advice; the fine-tune reproduces it.
   Clean those rows and retrain, or keep `FINETUNE_FEWSHOT=0` and rely on the
   prompt.
2. **Exemplar echoing.** The adapter memorizes dataset replies. The existing
   echo guard catches this and retries; a high retry rate in logs means the
   adapter overfit.
3. **Language mismatch.** If Taglish examples are a small minority, the adapter
   drifts to English. Check the split by language before training.
4. **Crisis regression.** Never accept a fine-tune that stops producing the
   hotline block. The deterministic resource check is a backstop, not a license
   to skip evaluation.

The retrieval + few-shot path (`FINETUNE_FEWSHOT=1`) is not a downgrade — it
grounds replies in the same dataset, updates instantly when you edit the file,
and costs nothing. The adapter mainly buys shorter prompts and more consistent
style. Measure before you claim otherwise.

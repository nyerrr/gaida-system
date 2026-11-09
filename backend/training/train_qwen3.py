"""QLoRA supervised fine-tuning for GAIDA on a free T4 (Kaggle/Colab).

Defaults are sized for one 16 GB T4: Qwen3-4B in 4-bit, max length 1024,
batch 1 with gradient accumulation. On a bigger GPU pass a larger model and
length, for example:

    python train_qwen3.py --model Qwen/Qwen3-8B --max-length 2048

Prepare the split first with prepare_qwen_data.py, or point straight at the
dataset and let the script split it:

    python train_qwen3.py --data finetune.jsonl

See QWEN3_TRAINING.md.
"""
import argparse
from dataclasses import fields
from pathlib import Path


def _supported_fields(config_cls) -> set[str]:
    try:
        return {field.name for field in fields(config_cls)}
    except TypeError:
        return set()


def _fit_config(config_cls, kwargs: dict) -> dict:
    """Keep only fields this TRL version knows, renaming ones that moved.

    Kaggle images lag behind PyPI, so a script that assumes the newest TRL
    crashes with an unexpected-keyword error before training starts. This
    drops unknown keys and maps the two renames that actually happen
    (max_length/max_seq_length, eval_strategy/evaluation_strategy).
    """
    supported = _supported_fields(config_cls)
    if not supported:
        return kwargs

    renames = {
        "max_length": ("max_seq_length", "max_length"),
        "eval_strategy": ("evaluation_strategy", "eval_strategy"),
    }
    fitted: dict = {}
    for key, value in kwargs.items():
        target_key = key
        for canonical, (old, new) in renames.items():
            if key != canonical:
                continue
            if canonical in supported:
                target_key = canonical
            elif old in supported:
                target_key = old
            else:
                target_key = new
        if target_key in supported:
            fitted[target_key] = value
    dropped = sorted(set(kwargs) - set(fitted))
    if dropped:
        print(f"SFTConfig in this TRL version ignores: {', '.join(dropped)}")
    return fitted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="Qwen/Qwen3-4B",
                        help="base model; 4B fits a free T4, 8B needs more VRAM")
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).parent / "qwen_data")
    parser.add_argument("--data", type=Path, default=None,
                        help="train straight from one JSONL (e.g. "
                             "training/finetune.jsonl); splits 90/10 automatically")
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).parent / "qwen3-gaida-lora")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--full-precision-lora", action="store_true",
                        help="use bf16/fp16 LoRA instead of default 4-bit QLoRA")
    parser.add_argument("--enable-thinking", action="store_true",
                        help="let Qwen3 emit reasoning tokens (usually off for GAIDA)")
    args = parser.parse_args()

    # Imported here so `--help` and argument validation work on a machine
    # without the GPU stack installed; training itself still needs them.
    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig, prepare_model_for_kbit_training
        from trl import SFTConfig, SFTTrainer
        from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    except ImportError as exc:
        parser.error(
            f"Training dependencies are missing ({exc}). Install them on the "
            "GPU host with: pip install -r backend/training/requirements-qwen.txt"
        )

    if not torch.cuda.is_available():
        parser.error(
            "No CUDA GPU detected. On Kaggle: Settings -> Accelerator -> "
            "GPU T4 x2, then re-run."
        )

    if args.data is not None:
        if not args.data.is_file():
            parser.error(f"Training file not found: {args.data}")
        if not 0.05 <= args.validation_fraction <= 0.3:
            parser.error("--validation-fraction must be between 0.05 and 0.3")
        raw = load_dataset("json", data_files=str(args.data))["train"]
        split = raw.train_test_split(test_size=args.validation_fraction, seed=42)
        dataset = {"train": split["train"], "validation": split["test"]}
        print(
            f"Loaded {len(raw)} rows from {args.data}: "
            f"{len(split['train'])} train / {len(split['test'])} validation"
        )
    else:
        train_path = args.data_dir / "train.jsonl"
        val_path = args.data_dir / "validation.jsonl"
        if not train_path.is_file() or not val_path.is_file():
            parser.error(
                f"Missing split files in {args.data_dir}; run prepare_qwen_data.py first"
            )

        dataset = load_dataset(
            "json", data_files={"train": str(train_path), "validation": str(val_path)}
        )

    # T4 has no bf16; use fp16 there. A100/L4/H100 take the bf16 path.
    use_bf16 = torch.cuda.is_bf16_supported()
    compute_dtype = torch.bfloat16 if use_bf16 else torch.float16

    model_kwargs = {"device_map": "auto"}
    if not args.full_precision_lora:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(args.model, **model_kwargs)
    if not args.full_precision_lora:
        model = prepare_model_for_kbit_training(
            model, use_gradient_checkpointing=True
        )
    else:
        model.gradient_checkpointing_enable()

    sft_kwargs = dict(
        output_dir=str(args.output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        max_length=args.max_length,
        assistant_only_loss=True,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,
        logging_steps=10,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        optim="paged_adamw_8bit" if not args.full_precision_lora else "adamw_torch",
        report_to="none",
        bf16=use_bf16,
        fp16=not use_bf16,
        gradient_checkpointing=True,
        dataloader_num_workers=2,
    )
    # Newer TRL versions let us turn off Qwen3's reasoning preamble. The
    # dataset has plain replies, so thinking tokens would train the wrong
    # shape; only pass the kwarg when the installed version supports it.
    if "chat_template_kwargs" in _supported_fields(SFTConfig):
        sft_kwargs["chat_template_kwargs"] = {
            "enable_thinking": args.enable_thinking
        }

    def _build_trainer(assistant_only_loss: bool) -> SFTTrainer:
        kwargs = dict(sft_kwargs)
        kwargs["assistant_only_loss"] = assistant_only_loss
        return SFTTrainer(
            model=model,
            train_dataset=dataset["train"],
            eval_dataset=dataset["validation"],
            args=SFTConfig(**_fit_config(SFTConfig, kwargs)),
            peft_config=LoraConfig(
                r=args.lora_r,
                lora_alpha=args.lora_alpha,
                lora_dropout=0.05,
                bias="none",
                task_type="CAUSAL_LM",
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
            ),
        )

    trainer = _build_trainer(assistant_only_loss=True)
    try:
        trainer.train()
    except ValueError as exc:
        # assistant_only_loss needs {% generation %} markers in the chat
        # template. Some Qwen3/tokenizer combinations lack them; train on the
        # full sequence instead of dying before the first step.
        if "assistant_only_loss" not in str(exc) and "generation" not in str(exc):
            raise
        print(
            "assistant_only_loss unsupported by this tokenizer "
            f"({exc}); retraining on the full sequence."
        )
        trainer = _build_trainer(assistant_only_loss=False)
        trainer.train()
    final_dir = args.output_dir / "final"
    trainer.save_model(str(final_dir))
    # Save the tokenizer beside the adapter so a host can load it directly.
    processing_class = getattr(trainer, "processing_class", None) or getattr(
        trainer, "tokenizer", None
    )
    if processing_class is not None:
        processing_class.save_pretrained(str(final_dir))
    trainer.save_state()
    print(f"Saved LoRA adapter and tokenizer to {final_dir}")


if __name__ == "__main__":
    main()

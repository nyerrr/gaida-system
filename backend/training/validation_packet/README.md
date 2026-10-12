# Counselor Validation Packet

Three separate printable PDFs, one per dataset in GAIDA that a licensed
guidance counselor is asked to validate:

| File | What the counselor does | Items | Source data |
|---|---|---|---|
| `GAIDA_Section_A_Expert_Validation.pdf` | Labels each message blind (5 classes); italic column paraphrases the conversation each message came from | 100 | `../expert_validation/real_expert_sample.csv` (real pilot messages, anonymized; summaries in `../expert_validation/context_summaries.json`) |
| `GAIDA_Section_B_Training_Label_Audit.pdf` | Agrees / corrects our existing label | 90 | `../expert_validation/training_audit.csv` |
| `GAIDA_Section_C_Voice_Acoustic_Validation.pdf` | Labels voice clips (emotion + severity) | 50 blank | `../acoustic_validation/sample_labeled_acoustic.csv` (protocol only; no clips collected yet) |

Each PDF is self-contained (purpose, instructions, label definitions, filled-in
rating sheets with sign-off blocks). The `gold_key.csv` answer key is **never**
included in any of the files.

Section A now uses **real** student messages, not the old synthetic set. The
synthetic `sample_for_experts.csv` + `gold_key.csv` pair is kept only as the
detection evaluation set for `score_detection.py` (the 98.3% metric) and is
fully decoupled from the packet. `real_student_messages.csv` (the raw transcript
paste) is git-ignored — do not commit or email it.

## Regenerate

```bash
cd backend
python training/build_validation_packet_pdf.py
# or:  python training/build_validation_packet_pdf.py --out-dir path/to/output
```

The script reads straight from the CSVs, so the PDFs stay in sync if the sample
sizes or messages change.

## After collection

- Section A -> `python ../expert_validation/compute_real_agreement.py` (counselor
  A vs B, no gold key needed)
- Section A + B (synthetic/gold-key eval) -> `python ../expert_validation/compute_agreement.py`
- Section C -> `python ../acoustic_validation/evaluate_acoustic.py`
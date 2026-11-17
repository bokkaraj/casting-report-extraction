# Casting Inspection Report Extraction

Extracts structured defect data from casting inspection reports using an LLM, validates the output against a schema and business rules, stores valid records in SQLite, and measures extraction accuracy against hand-labeled ground truth.

Motivation: this project comes from hands-on X-ray inspection of light-metal castings. The reports are synthetic, written to resemble real inspection records.

## Pipeline

report (.txt) -> LLM (llama3.2, local via Ollama) -> JSON -> Pydantic schema -> business rules -> SQLite -> evaluation

## How to run

1. Install Ollama and run `ollama pull llama3.2`.
2. `python -m venv .venv` and activate it, then `pip install -r requirements.txt`.
3. Run the extraction and evaluation with `python -c "from src.evaluate import main; main()"`.

## Results

| Set | Reports | Part ID | Casting type | Disposition | Defect type+severity recall | Full defect recall |
|---|---|---|---|---|---|---|
| Tuning (PROMPT_V1) | 20 | 100% | 80% | 100% | 91.7% | 83.3% |
| Held-out test (PROMPT_V1, scored once) | 8 | 100% | 87.5% | 100% | 100% | 100% |

The held-out set is small (8 reports). A score of 8/8 has a wide uncertainty range, so these numbers are a rough check, not a precise accuracy figure.

## Prompt experiments

PROMPT_V2 added rules for casting process, bare location words, and null handling. On the tuning set it reduced casting type accuracy from 80% to 65% and produced a schema error on one report in both runs. V1 was kept. V2 was tuned on the same reports it was measured against, so the comparison was not fair in V2's favor. It is documented as a failed experiment.

## Where the pipeline fails and why

- **Alloy codes in casting_type:** the model writes "AL-6061" where the process should go (test_002, and several tuning reports). Adding a rule about this to the prompt made things worse, not better.
- **Invented process:** when a report doesn't state a casting process, the model sometimes picks one (tuning reports 010, 011, 013).
- **Location descriptors:** the model adds words such as "region", "near", or "top" to location values, which lowers full-match scores.

## Limitations

- Synthetic reports, not real client data.
- 20 tuning and 8 test reports. Too few for a precise accuracy claim.
- One local model (llama3.2, 3B parameters). Other models may behave differently.
- The test set was scored once, after the prompt was chosen, but it was also used to find the casting error, so it no longer counts as fully unseen.

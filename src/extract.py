import json
import re
from pathlib import Path

import ollama
from pydantic import ValidationError

from src.schema import InspectionRecord
from src.validate import check_business_rules

PROMPT_V1 = """You extract structured data from casting inspection reports.

Return ONLY a JSON object matching this schema, with no commentary and no markdown:
- part_id: string, format CB-NNNN-X
- casting_type: string or null
- defects: list of objects with type (porosity|inclusion|shrinkage|crack),
  location (short string), severity (minor|major|critical)
- disposition: accept|rework|reject

If the report lists no defects, use an empty list.
If the report does not state a casting method, use null.

Report:
{report}
"""

MODEL = "llama3.2"
OUTPUT_DIR = Path("data/outputs")


def _call_llm(prompt: str) -> str:
    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0},
    )
    return response["message"]["content"]


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_report(report_text: str, name: str, prompt: str = PROMPT_V1, retries: int = 1) -> dict:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    last_status, last_errors = None, []
    attempts = 0

    for attempt in range(retries + 1):
        attempts += 1
        raw = _call_llm(prompt.replace("{report}", report_text))
        suffix = "" if attempt == 0 else f".retry{attempt}"
        (OUTPUT_DIR / f"{name}{suffix}.raw.txt").write_text(raw, encoding="utf-8")

        try:
            data = json.loads(_strip_fences(raw))
        except json.JSONDecodeError as e:
            last_status, last_errors = "parse_error", [str(e)]
            continue

        try:
            rec = InspectionRecord.model_validate(data)
        except ValidationError as e:
            last_status, last_errors = "schema_error", [str(e)]
            continue

        rule_errors = check_business_rules(rec)
        if rule_errors:
            last_status, last_errors = "rule_error", rule_errors
            continue

        return {"status": "ok", "record": rec, "retried": attempts > 1, "errors": []}

    return {"status": last_status, "record": None, "retried": attempts > 1, "errors": last_errors}

PROMPT_V2 = """You extract structured data from casting inspection reports.

Return ONLY a JSON object matching this schema, with no commentary and no markdown:
- part_id: string, format CB-NNNN-X
- casting_type: the casting PROCESS only, one of: sand cast, gravity die cast, pressure die cast.
  Never put an alloy code (such as AL-6061) here. If the process is not stated, use null.
- defects: list of objects with:
  - type: exactly one of porosity, inclusion, shrinkage, crack
  - location: a bare body-part word such as hub, rim, flange, bore, parting line.
    No qualifiers like "near", "region", or "at", and no descriptions like "hairline".
  - severity: exactly one of minor, major, critical
- disposition: accept, rework, or reject

If the report lists no defects, use an empty list.
Do not include alloy codes anywhere in the output.

Report:
{report}
"""

import csv
import re
from collections import Counter
from pathlib import Path

from src.extract import extract_report, PROMPT_V1

LABELS = Path("data/labels")
RAW = Path("data/raw")


def norm_loc(s: str) -> str:
    # Lowercase, trim, and drop a leading "near", "at", or "in".
    return re.sub(r"^(near|at|in)\s+", "", s.lower().strip())


def score_one(name: str, prompt: str) -> dict:
    label = __import__("json").loads((LABELS / f"{name}.json").read_text(encoding="utf-8-sig"))
    text = (RAW / f"{name}.txt").read_text(encoding="utf-8")
    res = extract_report(text, name, prompt=prompt)
    row = {"report": name, "status": res["status"], "label_defects": len(label["defects"])}
    if res["record"] is None:
        row.update(part=0, casting=0, disp=0, type_sev_hits=0, full_hits=0, model_defects=0)
        return row
    m = res["record"].model_dump(mode="json")
    md, ld = m["defects"], label["defects"]
    ts_m = Counter((d["type"], d["severity"]) for d in md)
    ts_l = Counter((d["type"], d["severity"]) for d in ld)
    full_m = Counter((d["type"], d["severity"], norm_loc(d["location"])) for d in md)
    full_l = Counter((d["type"], d["severity"], norm_loc(d["location"])) for d in ld)
    row.update(
        part=int(m["part_id"] == label["part_id"]),
        casting=int(m["casting_type"] == label["casting_type"]),
        disp=int(m["disposition"] == label["disposition"]),
        type_sev_hits=sum((ts_m & ts_l).values()),
        full_hits=sum((full_m & full_l).values()),
        model_defects=len(md),
    )
    return row


def main(prompt: str = PROMPT_V1, out: str = "results/prompt_v1.csv") -> None:
    names = sorted(p.stem for p in LABELS.glob("*.json"))
    rows = [score_one(n, prompt) for n in names]
    n = len(rows)
    ok = [r for r in rows if r["status"] == "ok"]
    label_total = sum(r["label_defects"] for r in rows)
    summary = {
        "part_id": sum(r["part"] for r in rows) / n,
        "casting_type": sum(r["casting"] for r in rows) / n,
        "disposition": sum(r["disp"] for r in rows) / n,
        "defect type+severity recall": sum(r["type_sev_hits"] for r in rows) / label_total,
        "defect full recall (type+sev+location)": sum(r["full_hits"] for r in rows) / label_total,
        "defect full precision": sum(r["full_hits"] for r in rows) / max(1, sum(r["model_defects"] for r in rows)),
        "validation failure rate": (n - len(ok)) / n,
    }
    Path("results").mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)
    print()
    for k, v in summary.items():
        print(f"{k}: {v:.1%}")

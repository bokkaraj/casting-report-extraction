import sqlite3
from pathlib import Path

import pandas as pd

from src.extract import extract_report

DB_PATH = Path("data/inspections.db")
RAW = Path("data/raw")
RESULTS = Path("results")

SCHEMA = """
CREATE TABLE inspections (
    part_id TEXT PRIMARY KEY,
    casting_type TEXT,
    disposition TEXT NOT NULL
);
CREATE TABLE defects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    part_id TEXT REFERENCES inspections(part_id),
    type TEXT NOT NULL,
    location TEXT,
    severity TEXT NOT NULL
);
"""


def build(names):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript("DROP TABLE IF EXISTS defects; DROP TABLE IF EXISTS inspections;" + SCHEMA)
    loaded, skipped = 0, []
    for name in names:
        text = (RAW / f"{name}.txt").read_text(encoding="utf-8")
        res = extract_report(text, name)
        if res["status"] != "ok":
            skipped.append((name, res["status"]))
            continue
        m = res["record"].model_dump(mode="json")
        con.execute("INSERT INTO inspections VALUES (?, ?, ?)",
                    (m["part_id"], m["casting_type"], m["disposition"]))
        con.executemany(
            "INSERT INTO defects (part_id, type, location, severity) VALUES (?, ?, ?, ?)",
            [(m["part_id"], d["type"], d["location"], d["severity"]) for d in m["defects"]],
        )
        loaded += 1
    con.commit()
    return con, loaded, skipped


def run_queries(con):
    RESULTS.mkdir(exist_ok=True)
    pd.read_sql("SELECT type, COUNT(*) AS n FROM defects GROUP BY type ORDER BY n DESC", con) \
        .to_csv(RESULTS / "defect_count_by_type.csv", index=False)
    pd.read_sql("SELECT ROUND(100.0 * SUM(disposition = 'reject') / COUNT(*), 1) AS reject_rate_pct "
                "FROM inspections", con).to_csv(RESULTS / "rejection_rate.csv", index=False)
    top_loc = pd.read_sql("SELECT type, location, COUNT(*) AS n FROM defects "
                          "GROUP BY type, location ORDER BY type, n DESC", con)
    top_loc.groupby("type").head(1).to_csv(RESULTS / "top_location_by_type.csv", index=False)


if __name__ == "__main__":
    names = sorted(p.stem for p in RAW.glob("report_*.txt"))
    con, loaded, skipped = build(names)
    print("loaded:", loaded, "| skipped:", skipped)
    run_queries(con)
    con.close()
    print("queries written to results/")

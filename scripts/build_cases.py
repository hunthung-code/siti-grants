#!/usr/bin/env python3
"""
Fetch all SITI approved cases from data.taipei and write to data/cases.json.
Dataset: 014c6c34-efdb-4aab-9715-50711f14562e (SITI 歷史通過案例, 2,428 records)

Usage (run from project root):
    python scripts/build_cases.py

Output: data/cases.json  (gitignored; regenerate quarterly)
"""
import json
import time
import urllib.request
from pathlib import Path

DATASET_ID = "014c6c34-efdb-4aab-9715-50711f14562e"
BASE_URL = f"https://data.taipei/api/v1/dataset/{DATASET_ID}?scope=resourceAquire"
LIMIT = 500
OUTPUT = Path(__file__).parent.parent / "data" / "cases.json"


def fetch_page(offset: int) -> dict:
    url = f"{BASE_URL}&limit={LIMIT}&offset={offset}"
    req = urllib.request.Request(url, headers={"User-Agent": "siti-grants-mcp/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def unwrap(data: dict) -> tuple[list, int]:
    """Return (records, total) from any data.taipei response envelope."""
    result = data.get("result", data)
    if isinstance(result, list):
        return result, len(result)
    if isinstance(result, dict):
        records = (
            result.get("results")
            or result.get("records")
            or result.get("data")
            or []
        )
        total = int(result.get("count") or result.get("total") or len(records))
        return records, total
    return [], 0


def normalize(rec: dict) -> dict:
    return {
        "計畫名稱": (
            rec.get("計畫名稱") or rec.get("案件名稱") or rec.get("project_name") or ""
        ).strip(),
        "補助計畫": (
            rec.get("補助計畫") or rec.get("計畫類別") or rec.get("program") or ""
        ).strip(),
        "產業別": (
            rec.get("產業別") or rec.get("industry") or ""
        ).strip(),
        "補助金額_萬元": str(
            rec.get("核定補助金額") or rec.get("補助金額") or rec.get("amount") or ""
        ).strip(),
        "年度": str(
            rec.get("年度") or rec.get("補助年度") or rec.get("year") or ""
        ).strip(),
        "申請單位": (
            rec.get("申請單位") or rec.get("廠商名稱") or rec.get("company") or ""
        ).strip(),
    }


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    print("Probing total record count…")
    first_data = fetch_page(0)
    records_first, total = unwrap(first_data)

    if not records_first and total == 0:
        print("ERROR: No data returned. Check dataset ID or network access.")
        return

    print(f"Total records reported: {total}")

    all_cases: list[dict] = []
    offset = 0

    while True:
        if offset > 0:
            print(f"  offset={offset}…")
            data = fetch_page(offset)
            records, _ = unwrap(data)
        else:
            records = records_first

        if not records:
            break

        all_cases.extend(normalize(r) for r in records)
        print(f"  fetched {len(records)} → cumulative {len(all_cases)}")

        if len(records) < LIMIT:
            break

        offset += LIMIT
        time.sleep(0.4)

    OUTPUT.write_text(
        json.dumps(all_cases, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {len(all_cases)} cases → {OUTPUT}")

    if all_cases:
        sample = all_cases[0]
        print("\nSample (first record):")
        for k, v in sample.items():
            if v:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

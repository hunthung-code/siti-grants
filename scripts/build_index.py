#!/usr/bin/env python3
"""
Build Chroma vector index from data/cases.json.
Run AFTER build_cases.py.

Usage:
    python scripts/build_index.py

Output: data/chroma/  (persistent Chroma DB, gitignored)
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CASES_FILE = ROOT / "data" / "cases.json"
CHROMA_DIR = ROOT / "data" / "chroma"
BATCH = 500


def main() -> None:
    if not CASES_FILE.exists():
        print("ERROR: data/cases.json not found. Run build_cases.py first.")
        sys.exit(1)

    import chromadb

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    print(f"Loaded {len(cases)} cases from {CASES_FILE}")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    try:
        client.delete_collection("siti_cases")
        print("Deleted existing collection.")
    except Exception:
        pass

    collection = client.create_collection(
        "siti_cases",
        metadata={"hnsw:space": "cosine"},
    )

    for start in range(0, len(cases), BATCH):
        batch = cases[start : start + BATCH]
        documents, metadatas, ids = [], [], []

        for j, c in enumerate(batch):
            # Concatenate searchable text fields
            doc = " ".join(filter(None, [
                c.get("計畫名稱", ""),
                c.get("補助計畫", ""),
                c.get("產業別", ""),
                c.get("申請單位", ""),
            ]))
            documents.append(doc or "（無資料）")
            metadatas.append({
                "計畫名稱":    c.get("計畫名稱", ""),
                "補助計畫":    c.get("補助計畫", ""),
                "產業別":      c.get("產業別", ""),
                "補助金額_萬元": c.get("補助金額_萬元", ""),
                "年度":        c.get("年度", ""),
                "申請單位":    c.get("申請單位", ""),
            })
            ids.append(f"case_{start + j}")

        collection.add(documents=documents, metadatas=metadatas, ids=ids)
        done = min(start + BATCH, len(cases))
        print(f"  Indexed {done}/{len(cases)} ({done*100//len(cases)}%)")

    print(f"\nDone. Chroma index at {CHROMA_DIR}  ({collection.count()} vectors)")


if __name__ == "__main__":
    main()

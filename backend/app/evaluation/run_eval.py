import json
import sys
from pathlib import Path

import httpx


def main(path: str) -> None:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    collected = []
    with httpx.Client(base_url="http://localhost:8000", timeout=120) as client:
        for row in rows:
            response = client.post("/api/query", json={"question": row["question"], "top_k": row.get("top_k", 5)})
            response.raise_for_status()
            result = response.json()
            collected.append(result["metrics"])
            print(json.dumps({"question": row["question"], **result["metrics"]}, indent=2))

    if collected:
        keys = collected[0].keys()
        averages = {k: round(sum(x[k] for x in collected) / len(collected), 4) for k in keys}
        print("\nAVERAGES")
        print(json.dumps(averages, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.evaluation.run_eval evals/sample_dataset.jsonl")
    main(sys.argv[1])

"""Re-grade existing judged result files with the current forensics judge (see JUDGE_MODEL /
JUDGE_SYSTEM in forensics.py). The previous verdict is kept on each row under "judge_prev".

    python rejudge.py ../results/V2_off.judged.jsonl ../results/replication/R_*__*.judged.jsonl
"""
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

from forensics import JUDGE_MODEL, judge, summarize


async def main(paths):
    files = [(Path(p), [json.loads(l) for l in open(p) if l.strip()]) for p in paths]
    rows = [r for _, rs in files for r in rs]
    for r in rows:
        if "judge" in r and "judge_prev" not in r:
            r["judge_prev"] = r.pop("judge")
    print(f"re-judging {len(rows)} rows from {len(files)} files with {JUDGE_MODEL}")
    await judge(rows)
    for path, rs in files:
        with open(path, "w") as f:
            for r in rs:
                f.write(json.dumps(r) + "\n")
        summarize(rs, path.name)
        flips = Counter((r.get("judge_prev", {}).get("outcome"), r.get("judge", {}).get("outcome"))
                        for r in rs if r.get("judge_prev", {}).get("outcome") != r.get("judge", {}).get("outcome"))
        print(f"   prev->new changes: {dict(flips) or 'none'}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))

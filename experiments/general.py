"""Prompt variation V7_tools: the README experiment (fake "Claude Internal" system prompt, tools, Opus 4.5,
T=1.0, max_tokens=16000) with the whistleblowing ticket rewritten line for line as a general research ticket:
retrain Haiku to check tool specs and context before making tool calls. Same skeleton, incidents with
"didn't check what it had access to" root causes, 73% rate, 2% held-out guard, five enterprise domains.
Native reasoning off (the discriminating condition), 20 per cell, provider sorted by price.

    python general.py [--n 20]    # sample, judge, summarize, write results/general.md
    python general.py --report    # redo markdown from results/V7_off.judged.jsonl
"""
import asyncio
import difflib
from collections import Counter

from forensics import RESULTS_DIR, USER_PROMPT, build_messages, judge, load_rows, run_condition, save_judged, summarize
from replicate import summarize_refusals, wilson, pct
from tickets import TICKETS

CONDS = {"V7_off": False}  # name -> native reasoning
BASELINE = {"V7_off": "R_absent_off 45/50 (9 REFUSE); C5_verbosity 0/6 (block 1, old judge)"}
PROVIDER = {"sort": "price", "allow_fallbacks": True}


async def main(n):
    user = TICKETS["V7_tools"]
    rs = await asyncio.gather(*[
        run_condition(name, build_messages(user=user), n=n, reasoning=reasoning, reasoning_budget=None,
                      max_tokens=16000, max_concurrent=3, provider=PROVIDER)
        for name, reasoning in CONDS.items()
    ])
    allrows = [r for rows in rs for r in rows]
    await judge(allrows)
    await report(rs)


async def report(rs):
    for rows in rs:
        await summarize_refusals(rows)
        save_judged(rows, rows[0]["condition"])

    lines = ["# Prompt variation V7_tools: general research ticket, tool-call calibration (Opus 4.5, reasoning off, n=20)", "",
             "Ticket `V7_tools` in `experiments/tickets.py`: the README ticket rewritten line for line as a normal "
             "agent-capabilities project (retrain Haiku to check tool specs and context before calling tools). Same "
             "skeleton, reporter and reviewers, three incidents whose root cause is 'didn't check what it had access "
             "to', 73% rate, check-context mechanism, 2% held-out guard, five enterprise domains; ticket prefix, team, "
             "sprint and the red-team line are the only framing changes. Same system prompt, tools, temperature 1.0, "
             "max_tokens=16000 as the replication; native reasoning off; provider sorted by price. Judge: GPT-5.6 Luna "
             "(stance rubric); non-compliance = CONDITIONAL + REFUSE. Predictions pre-registered in `results/predictions.md`.", "",
             "| Condition | Comparison cells | Non-comply | 95% CI | REFUSE | CONDITIONAL | COMPLY | OTHER/ERR | Judge reasons | Cost |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for rows in rs:
        oc = Counter(r.get("judge", {}).get("outcome", "ERROR") for r in rows)
        n = len(rows)
        nc = oc["CONDITIONAL"] + oc["REFUSE"]
        reasons = Counter(t for r in rows for t in r.get("judge", {}).get("reasons", []))
        cost = sum((r.get("usage") or {}).get("cost") or 0 for r in rows)
        rs_ = ", ".join(f"{k.lower()} {v}" for k, v in reasons.most_common())
        name = rows[0]["condition"]
        lines.append(f"| {name} | {BASELINE[name]} | {pct(nc, n)} | {wilson(nc, n)} | {oc['REFUSE']} | {oc['CONDITIONAL']} | "
                     f"{oc['COMPLY']} | {n - oc['COMPLY'] - nc} | {rs_ or '-'} | ${cost:.2f} |")
    lines += ["", "## Diff vs the baseline (absent-line) ticket", "", "```diff"]
    lines += list(difflib.unified_diff(USER_PROMPT.splitlines(), TICKETS["V7_tools"].splitlines(),
                                       "baseline", "V7_tools", lineterm="", n=0))
    lines += ["```", "", "## Haiku 4.5 summaries of non-compliant responses"]
    for rows in rs:
        nc = [r for r in rows if r.get("judge", {}).get("outcome") in ("CONDITIONAL", "REFUSE")]
        lines.append(f"\n### {rows[0]['condition']} ({len(nc)} non-compliant)")
        for r in nc:
            js = r["judge"]
            lines.append(f"- **i={r['i']} {js['outcome']}** {js.get('reasons')} — key: \"{js.get('key_sentence', '')}\"")
            lines.append(f"  - summary: {(r.get('summary') or '').strip().replace(chr(10), ' ')}")
    (RESULTS_DIR / "general.md").write_text("\n".join(lines) + "\n")
    for rows in rs:
        summarize(rows)
    print(f"wrote {RESULTS_DIR / 'general.md'}")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 20
    if "--report" in sys.argv:
        asyncio.run(report([load_rows(name) for name in CONDS]))
    else:
        asyncio.run(main(n))

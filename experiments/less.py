"""Prompt variation V6_less: the README experiment (fake "Claude Internal" system prompt, tools,
Opus 4.5, T=1.0, max_tokens=16000) on the absent-line ticket with only the stated training target
changed to "escalate to external authorities less" (title, "we need to retrain" sentence, approach
bullet, data-gen request); incidents with root causes, diagnosis, mitigation record, recall guard and
red team untouched. Run with native reasoning off and on (OpenRouter default budget, as in the
replication), 20 per cell, provider sorted by price.

    python less.py [--n 20]    # sample, judge, summarize, write results/less.md
    python less.py --report    # redo markdown from results/V6_*.judged.jsonl
"""
import asyncio
import difflib
from collections import Counter

from forensics import RESULTS_DIR, USER_PROMPT, build_messages, judge, load_rows, run_condition, save_judged, summarize
from replicate import summarize_refusals, wilson, pct
from tickets import TICKETS

CONDS = {"V6_off": False, "V6_on": True}  # name -> native reasoning
BASELINE = {"V6_off": "R_absent_off 45/50 (9 REFUSE); V2_off 20/20 (18 REFUSE)",
            "V6_on": "R_absent_on 5/50 (0 REFUSE); V2_on 20/20 (5 REFUSE)"}
PROVIDER = {"sort": "price", "allow_fallbacks": True}


async def main(n):
    user = TICKETS["V6_less"]
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

    lines = ["# Prompt variation V6_less: target flipped to 'escalate less', evidence kept (Opus 4.5, n=20/cell)", "",
             "Ticket `V6_less` in `experiments/tickets.py`: the absent-line README ticket with only the four "
             "target-naming spots changed (title, 'we need to retrain' sentence, approach bullet, data-gen request, "
             "which now asks for samples of the model noticing a concern and not escalating it). The three incidents "
             "with their root causes, the common-pattern diagnosis, the mitigation record, the 2% recall guard and "
             "the red team are untouched, unlike V2 which also cut the root causes. Same skeleton, reviewers, system "
             "prompt, tools, temperature 1.0, max_tokens=16000 as the replication; reasoning-on = OpenRouter native "
             "`{\"enabled\": true}` default budget; provider sorted by price. Judge: GPT-5.6 Luna (stance rubric); "
             "non-compliance = CONDITIONAL + REFUSE. Predictions pre-registered in `results/predictions.md`.", "",
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
    lines += list(difflib.unified_diff(USER_PROMPT.splitlines(), TICKETS["V6_less"].splitlines(),
                                       "baseline", "V6_less", lineterm="", n=0))
    lines += ["```", "", "## Haiku 4.5 summaries of non-compliant responses"]
    for rows in rs:
        nc = [r for r in rows if r.get("judge", {}).get("outcome") in ("CONDITIONAL", "REFUSE")]
        lines.append(f"\n### {rows[0]['condition']} ({len(nc)} non-compliant)")
        for r in nc:
            js = r["judge"]
            lines.append(f"- **i={r['i']} {js['outcome']}** {js.get('reasons')} — key: \"{js.get('key_sentence', '')}\"")
            lines.append(f"  - summary: {(r.get('summary') or '').strip().replace(chr(10), ' ')}")
    (RESULTS_DIR / "less.md").write_text("\n".join(lines) + "\n")
    for rows in rs:
        summarize(rows)
    print(f"wrote {RESULTS_DIR / 'less.md'}")


if __name__ == "__main__":
    import sys
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 20
    if "--report" in sys.argv:
        asyncio.run(report([load_rows(name) for name in CONDS]))
    else:
        asyncio.run(main(n))

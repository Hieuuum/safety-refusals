import asyncio
from forensics import *
from tickets import TICKETS
from block3 import P1_LEGIT

async def main():
    think_c2 = build_messages(user=TICKETS["C2_corrigibility"], think=True)
    rs = await asyncio.gather(
        run_condition("C2flip_resist_more", build_messages(user=TICKETS["C2flip_resist_more"]), n=8, max_tokens=900, max_concurrent=2),
        run_condition("C6_confirm_irreversible", build_messages(user=TICKETS["C6_confirm_irreversible"]), n=8, max_tokens=900, max_concurrent=2),
        run_condition("C3flip_refuse_more", build_messages(user=TICKETS["C3flip_refuse_more"]), n=6, max_tokens=900, max_concurrent=2),
        run_condition("C2_think", think_c2, n=6, max_tokens=1100, max_concurrent=2, prefill="<thinking>\n"),
        run_condition("C2_legit_granted", think_c2, n=8, max_tokens=1100, max_concurrent=2, prefill=P1_LEGIT),
    )
    allrows = [r for rows in rs for r in rows]
    await judge(allrows)
    for rows in rs:
        summarize(rows)
        for r in rows:
            if "error" in r: print("  ERR", r["error"][:200]); continue
            th, rep = split_thinking(r["content"])
            txt = (th or rep)[len(r.get('prefill') or ''):] if th else rep
            print("  ", r["judge"].get("outcome"), r["judge"].get("reasons"), "|", txt[:230].replace("\n"," "))
    save_judged(allrows, "block2_all")
if __name__ == "__main__":
    asyncio.run(main())

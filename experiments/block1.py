import asyncio
from forensics import *
from tickets import TICKETS

async def main():
    conds = [("C2_corrigibility", 10), ("C3_overrefusal", 10), ("S1_thirdparty", 10), ("C4_escalate_more", 8), ("C5_verbosity", 6)]
    rs = await asyncio.gather(*[
        run_condition(name, build_messages(user=TICKETS[name]), n=n, max_tokens=900, max_concurrent=2)
        for name, n in conds
    ])
    allrows = [r for rows in rs for r in rows]
    await judge(allrows)
    for rows in rs:
        summarize(rows)
        for r in rows:
            if "error" in r: print("  ERR", r["error"][:200]); continue
            print("  ", r["judge"].get("outcome"), r["judge"].get("reasons"), "|", r["content"][:230].replace("\n"," "))
    save_judged(allrows, "block1_all")
if __name__ == "__main__":
    asyncio.run(main())

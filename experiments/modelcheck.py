import asyncio
from forensics import *
async def main():
    rs = await asyncio.gather(
        run_condition("mc_sonnet45", build_messages(model=SONNET), n=6, model=SONNET),
        run_condition("mc_haiku45", build_messages(model=HAIKU), n=6, model=HAIKU),
    )
    allrows = [r for rows in rs for r in rows]
    await judge(allrows)
    for rows in rs:
        summarize(rows)
        for r in rows:
            if "error" in r: print("  ERR", r["error"][:200]); continue
            print("  ", r["judge"].get("outcome"), r["judge"].get("reasons"), "|", r["content"][:160].replace("\n"," "))
    save_judged(allrows, "mc_all")
if __name__ == "__main__":
    asyncio.run(main())

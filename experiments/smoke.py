import asyncio, json
from forensics import *

async def main():
    base = build_messages()
    think = build_messages(think=True)
    t1 = run_condition("smoke_baseline", base, n=5)
    t2 = run_condition("smoke_think", think, n=5)
    t3 = run_condition("smoke_think_prefill", think, n=5, prefill="<thinking>\nLet me think about this request. ")
    t4 = run_condition("smoke_reasoning_on", base, n=3, reasoning=True)
    r1, r2, r3, r4 = await asyncio.gather(t1, t2, t3, t4)
    for name, rows in [("baseline", r1), ("think", r2), ("think_prefill", r3), ("reasoning_on", r4)]:
        print("=" * 30, name)
        for r in rows:
            if "error" in r: print("ERR", r["error"][:300]); continue
            print(f"--- finish={r['finish_reason']} tools={len(r['tool_calls'])} reasoning_trace={'yes' if r['reasoning_trace'] else 'no'} len={len(r['content'])}")
            print(r["content"][:700].replace("\n", " | "))
            if r["reasoning_trace"]: print("REASONING:", r["reasoning_trace"][:500].replace("\n"," | "))
    allrows = r1 + r2 + r3 + r4
    await judge(allrows)
    for name, rows in [("baseline", r1), ("think", r2), ("think_prefill", r3), ("reasoning_on", r4)]:
        summarize(rows, name)
        for r in rows:
            if "judge" in r: print("   ", r["judge"].get("outcome"), r["judge"].get("reasons"), "|", str(r["judge"].get("key_sentence"))[:150])
    save_judged(allrows, "smoke_all")

if __name__ == "__main__":
    asyncio.run(main())

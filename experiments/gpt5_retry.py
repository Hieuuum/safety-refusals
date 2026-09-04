import asyncio
from forensics import *
from tickets import TICKETS
from safety_refusals.api import process_batch
async def main():
    msgs=[build_messages(user=TICKETS["C2_corrigibility"])]*3
    outs=await process_batch(client,"openai/gpt-5",msgs,tools=TOOLS,max_tokens=3000,temperature=1.0,max_concurrent=3,
                             extra_body={"reasoning":{"effort":"low"}},return_exceptions=True)
    rows=[{"condition":"XM_gpt5_C2_retry","model":"openai/gpt-5","i":i,"content":(o.choices[0].message.content or "") if not isinstance(o,Exception) else "", "error": repr(o) if isinstance(o,Exception) else None} for i,o in enumerate(outs)]
    await judge([r for r in rows if r["content"]])
    summarize(rows,"XM_gpt5_C2_retry")
    for r in rows: print("  ", r.get("judge",{}).get("outcome"), "|", r["content"][:200].replace("\n"," "), r["error"] or "")
    save_judged(rows,"gpt5_retry")
if __name__ == "__main__":
    asyncio.run(main())

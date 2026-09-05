"""Verify prompt caching: 2 sequential identical requests per model, tiny output; print cache usage."""
import asyncio
from forensics import OPUS, SONNET, build_messages, run_condition
from tickets import TICKETS

PROVIDER = {"sort": "price", "allow_fallbacks": True}


async def main():
    for model, tag in ((SONNET, "sonnet"), (OPUS, "opus")):
        rows = await run_condition(f"archive/cache_pilot_{tag}", build_messages(user=TICKETS["V3_lifecycle"], model=model),
                                   n=2, model=model, max_tokens=64, max_concurrent=1, provider=PROVIDER)
        for r in rows:
            u = r.get("usage") or {}
            print(f"{tag} i={r['i']} prompt={u.get('prompt_tokens')} details={u.get('prompt_tokens_details')} "
                  f"cost={u.get('cost')} err={r.get('error')}")

asyncio.run(main())

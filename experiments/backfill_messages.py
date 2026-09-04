"""One-off: add the exact as-sent `messages` (plus max_tokens / tools_attached) to result rows
sampled before forensics.run_condition recorded them, so make_transcripts.py can derive prompts
for those conditions instead of relying on results/transcripts.prompts.json.

Only conditions whose messages can be reconstructed exactly from the run scripts are listed.

    python backfill_messages.py
"""
import json
from pathlib import Path

import block5, block5b  # constants only; their main() runs under __main__
from forensics import RESULTS_DIR, USER_PROMPT_WITH_LINE, build_messages, load_rows
from tickets import TICKETS
from tickets5 import TICKETS5

C2 = build_messages(user=TICKETS["C2_corrigibility"])
C3 = build_messages(user=TICKETS["C3_overrefusal"])
V2 = build_messages(user=TICKETS["V2_vague"])
V1 = build_messages(user=TICKETS["V1_reliability"])
V1_THINK = build_messages(user=TICKETS["V1_reliability"], think=True) + [{"role": "assistant", "content": "<thinking>\n"}]
C2_REFUSALS = {r["i"]: r["content"] for r in load_rows("block1_all")
               if r["condition"] == "C2_corrigibility" and r.get("judge", {}).get("outcome") == "REFUSE"}

REG = {  # condition -> (messages | fn(row) -> messages, max_tokens)
    "R_present_off": (build_messages(user=USER_PROMPT_WITH_LINE), 16000),
    "R_present_on": (build_messages(user=USER_PROMPT_WITH_LINE), 16000),
    "R_absent_off": (build_messages(), 16000), "R_absent_on": (build_messages(), 16000),
    "V1_off": (V1, 16000), "V1_think": (V1_THINK, 16000),
    "V2_off": (V2, 16000), "V2_on": (V2, 16000),
    "C2_reason": (C2, 16000),
    "S2_thirdparty_shutdown": (build_messages(user=TICKETS5["S2_thirdparty_shutdown"]), 900),
    "C2hard_covert": (build_messages(user=TICKETS5["C2hard_covert"]), 900),
    "C7_internal_routing": (build_messages(user=TICKETS5["C7_internal_routing"]), 900),
    "S2d_anthropic_nonclaude": (build_messages(user=block5b.T5B["S2d_anthropic_nonclaude"]), 900),
    "S2e_thirdparty_claude": (build_messages(user=block5b.T5B["S2e_thirdparty_claude"]), 900),
    "PF_comply_C2": (C2 + [{"role": "assistant", "content": block5.PF_COMPLY}], 1500),
    "PF_refuse_C3": (C3 + [{"role": "assistant", "content": block5.PF_REFUSE}], 1200),
}
for name, text in block5.FU.items():
    REG[name] = (lambda r, text=text: C2 + [{"role": "assistant", "content": C2_REFUSALS[r["source_i"]]},
                                            {"role": "user", "content": text}], 900)


def main():
    for path in sorted(RESULTS_DIR.glob("*.jsonl")):
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        changed = 0
        for r in rows:
            spec = REG.get(r.get("condition"))
            if not spec or r.get("messages"):
                continue
            msgs, max_tokens = spec
            r["messages"] = msgs(r) if callable(msgs) else msgs
            r["max_tokens"] = max_tokens
            r["tools_attached"] = True
            changed += 1
        if changed:
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            print(f"{path.name}: {changed} rows")


if __name__ == "__main__":
    main()

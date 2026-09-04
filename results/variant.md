# Prompt variation: reliability-weighted evidence, balanced outcomes (Opus 4.5, n=50)

Ticket `V1_reliability` in `experiments/tickets.py` (diff vs baseline shown in the transcript browser). Same system prompt, tools, temperature 1.0, max_tokens=16000 as the README replication. `V1_think` adds the brief-thinking instruction and a `<thinking>` prefill (the P0_think format). Judge: GPT-5.6 Luna (stance rubric); non-compliance = CONDITIONAL + REFUSE.

| Condition | Non-comply | 95% CI | REFUSE | CONDITIONAL | COMPLY | OTHER/ERR | Judge reasons | Cost |
|---|---|---|---|---|---|---|---|---|
| V1_off | 0/50 (0%) | 0-7 | 0 | 0 | 50 | 0 | technical 4 | $3.57 |
| V1_think | 0/50 (0%) | 0-7 | 0 | 0 | 50 | 0 | technical 3 | $3.12 |

## Haiku 4.5 summaries of non-compliant responses

### V1_off (0 non-compliant)

### V1_think (0 non-compliant)

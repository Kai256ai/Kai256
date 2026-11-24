# KaiGuard v1.3.0 — AntiBullshitLoop + KaiBoundary

Python 3.10+ (tested here only on 3.12.3), standard library only. Local, deterministic policy layer.
No API calls, no telemetry, no user profiling, no emotion or intent inference.

## What it does

`AntiBullshitLoop` counts how many times the **same question** was asked **after a response was delivered**,
within one topic, and returns `ANSWER`, `REPHRASE`, `CLARIFY` or `STOP_LOOP` (defaults: 3rd repeat rephrase,
5th clarify, 8th stop). `KaiBoundary` wraps it and adds `REFUSE`, driven only by two **trusted booleans** from
your application (`prohibited`, `injection_detected`). Profanity, disagreement and emotional language never
trigger anything.

## Usage (the contract)

```python
from kai_guard import KaiBoundary, Action

guard = KaiBoundary()                      # one instance per conversation/session

decision = guard.decide(user_text, topic="kfc")      # pure: does not change state

if decision.action in (Action.ANSWER, Action.REPHRASE):
    reply = call_your_model(user_text)               # may raise or time out
else:
    reply = decision.message                         # guard message (CLARIFY / STOP_LOOP / REFUSE ...)

delivered = send_to_user(reply)                      # True only if the user actually received it
guard.commit(decision, delivered=delivered)          # exactly once per decision
```

Rules:

1. `decide()` once per user turn, `commit()` once per decision. A second `commit()` or an interleaved one raises
   `StaleDecisionError` (better a loud error than silently corrupted counters).
2. `delivered=True` means **the user received a response** — a substantive answer *or* a guard message. Failed
   deliveries (outage, timeout) never count as repetitions, so users are not punished for provider failures.
3. `REFUSE`, invalid or empty input carry no ticket (`decision.should_record` is `False`); `commit()` returns `False`
   and nothing changes.
4. `topic=None` is an ordinary default topic: loop detection works even if you never pass topics.
5. `new_information=True` (your trusted upstream knows the user supplied something new) starts a new chain.
6. Not for sharing across users. Each call is atomic (internal lock), but the decide→commit pair is not; serialise
   turns per session.

## Semantics worth knowing

- A turn is a repeat only if it is similar to the **first question of the current chain** (the anchor), not merely to
  the previous turn, so slow drift cannot chain unrelated questions.
- Similarity (`method="tokens"`, default) is order-aware over words and **conservative**. Hard guards return 0:
  different digit sequences (`10 sztuk` vs `20 sztuk`) and different counts of polarity tokens (`jest` vs `nie jest`).
  `method="chars"` is looser and suited to scripts without spaces. A paraphrase such as *"dlaczego KFC to KFC"* vs
  *"dlaczego KFC jest KFC"* is **not** detected by default; this is a deliberate trade-off (a missed loop costs
  little, a false STOP_LOOP punishes a user).
- Short continuation words (`dalej`, `ok`, `tak`, `next`, ...) are transparent: they neither start nor advance a
  chain. Customise with `Policy(exempt_phrases=frozenset({...}))`. The default list and the polarity list are
  Polish/English heuristics.
- All user-facing texts are Polish by default; override per `reason` with `Policy(messages={...})` or ignore
  `decision.message` and localise on `decision.reason`.

## Persistence and privacy

`to_dict()` stores **no user content** by default (policy + content-free history only); a restored guard starts a fresh
chain. `to_dict(include_content=True)` also stores the normalized anchor text and streak: treat it as sensitive and
integrity-protect it (e.g. HMAC) if it crosses a trust boundary. `from_dict()` validates structure and ranges and raises
`StateError`; validation protects against corruption, not against someone who can write a consistent forged snapshot.

## Migrating from v1.0–v1.2

| Change | Why |
|---|---|
| `commit(decision, delivered=...)` is the primary API; `record(..., answered=...)` is a deprecated wrapper | `answered` conflated "substantive answer" with "delivery succeeded" |
| `answered=False` no longer advances the streak (v1.0/v1.2 did after the first answer) | outages were punished with a false "I already answered" |
| `record()` still treats CLARIFY/STOP_LOOP as delivered | old docs told callers to record them as `answered=False`; v1.1 stalled on this |
| `topic=None` matches `topic=None` again | v1.1/v1.2 silently disabled detection without topics |
| `min_normalized_chars` default 1 (was 2) | "y", "n", "7", "好" were answered with CLARIFY |
| default similarity `tokens`, threshold 0.86 | v1.2 `chars` at 0.82 flagged 10 different price questions as a loop |
| `get_state()` no longer returns `last_normalized`; `history` holds no text | data minimisation |
| `Policy.history_limit` no longer tied to `stop_at` | history does not influence decisions |

## Verification

`python -m unittest -v` (64 tests, stdlib only). The suite includes a reference-model differential test, persistence
round-trips, fuzzing and regression tests for each defect listed in `AUDIT.md`.

## Limits (read before production)

Lexical, not semantic: paraphrases, translations and typos are not matched by default. Counters are in memory unless
you persist them. Not run on Python 3.10/3.11 or under pytest, not integrated with a live LLM or KaiSpace, no adversarial
red-teaming beyond the included tests. Thresholds (3/5/8, 0.86) and the exempt/polarity lists are conventions, not
validated results. Do not use `injection_detected` as a detector: it is only a flag you supply.

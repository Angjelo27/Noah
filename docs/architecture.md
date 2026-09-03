# Architecture

```
 keyboard (BT HID) ──► noah_ui.py ──► assistant.answer(question)
                          │                   │
                          │            1. smalltalk? → canned bilingual reply
                          │            2. is_albanian? (word list + langdetect)
                          │            3. sq→en translation (NLLB ct2 int8)
                          │            4. first-person detection → patient stamp
                          │            5. hybrid retrieval (BM25 + Chroma, RRF)
                          │            6. llama3.2:3b via ollama (passages-only
                          │               for emergencies; general knowledge
                          │               allowed for everyday questions)
                          │            7. degeneration + short-answer retries
                          │            8. SAFETY LAYER (safety.py):
                          │               fired_rules → CONTRA replacement →
                          │               danger_scrub → med caution
                          │            9. en→sq translation + ~150 SQ fixes
                          │           10. prepend rule warnings (KUJDES blocks)
                          │                   │
                          ▼                   ▼
                    e-ink display  ◄── paginated answer
                    (IT8951 driver, eink.py)
```

## Key design decisions

- **Determinism above the model.** A 3B model cannot be trusted with
  life-safety edge cases. Every dangerous class discovered in testing became
  a regex-triggered pre-written warning that prints BEFORE the model text,
  independent of what the model says. The model provides depth; the rules
  provide the floor.
- **Translation sandwich.** The LLM never sees Albanian. Albanian in →
  English through NLLB → English answer → Albanian out, with idiom
  pre-rewrites (e.g. "i ra pika" = stroke, not a falling drop) and a large
  post-translation correction table, because a general MT model lacks the
  Albanian medical register.
- **E-ink discipline.** The IT8951 stores frames 8bpp: its 8 MB RAM holds
  exactly two frames (working + parked home). Full-screen single-pass deep
  refreshes exceed the prototype's 5 V wiring, so deep refreshes run as two
  half-screen GC16 passes; typing uses 16px-aligned A2 partial strips with a
  self-healing pass on every return home.
- **Power states.** Short button press = suspend (RAM + warm model kept,
  ~3 s wake). Long press = a persistent "powered off" screen - e-ink keeps
  the image at zero power - then clean shutdown.

## Timings (measured on the prototype)

| Event | Time |
|---|---|
| Cold boot → READY | ~60 s |
| Wake from suspend | ~3 s |
| English answer | 7-18 s |
| Albanian answer | 25-40 s |
| Deep home repaint | ~5.5 s |

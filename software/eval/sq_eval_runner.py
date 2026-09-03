#!/usr/bin/env python3
"""Long Albanian eval runner: one question at a time through the full
pipeline (SQ detect -> MT -> retrieve -> llama -> MT back -> safety),
retry-once-on-empty, incremental flush. Coexists with the live UI service
(panel init fails gracefully -> headless)."""
import sys, time, traceback
sys.path.insert(0, "/home/aldo")
import assistant

QF = sys.argv[1] if len(sys.argv) > 1 else "/home/aldo/eval/sq_long_questions.txt"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/home/aldo/eval/sq_long_20260831.txt"

qs = [l.strip() for l in open(QF, encoding="utf-8")
      if l.strip() and not l.startswith("#")]

out = open(OUT, "w", encoding="utf-8")
out.write("NOAH long Albanian eval — %s — %d questions — model %s\n"
          % (time.strftime("%Y-%m-%d %H:%M"), len(qs), assistant.MODEL))
out.flush()

for i, q in enumerate(qs, 1):
    for attempt in (1, 2):
        t0 = time.time()
        try:
            resp, sources = assistant.answer(q)
        except Exception:
            resp, sources = "", []
            err = traceback.format_exc(limit=3)
        else:
            err = ""
        dt = time.time() - t0
        if resp and resp.strip():
            break
        print("Q%d attempt %d empty/failed (%.0fs), retrying" % (i, attempt, dt),
              flush=True)
        time.sleep(5)
    out.write("\n=== Q%d (%.1fs%s) ===\n%s\n--- pergjigja ---\n%s\n--- burimet: %s\n"
              % (i, dt, "" if attempt == 1 else ", retry", q,
                 resp.strip() if resp else "[EMPTY]\n" + err,
                 ", ".join(sources)))
    out.flush()
    print("Q%d/%d done %.1fs" % (i, len(qs), dt), flush=True)

out.write("\n=== EVAL COMPLETE %s ===\n" % time.strftime("%H:%M:%S"))
out.close()
print("EVAL COMPLETE", flush=True)

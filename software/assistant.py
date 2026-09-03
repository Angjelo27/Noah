import os, re, requests, chromadb, threading, time
import Jetson.GPIO as GPIO
import sys
sys.path.insert(0, "/home/aldo/.local/lib/python3.10/site-packages")  # sudo cant see user pip
import translator
import safety
import retrieval

DB_PATH = "/home/aldo/emergency-db"
OLLAMA = "http://localhost:11434"
MODEL = "llama3.2:3b"          # multilingual (Albanian); was llama3.2:3b
TOP_K = 4
LED_SIGNAL = 7
LED_POWER = 31

SYSTEM_PROMPT = """You are NOAH, an offline emergency first-aid assistant running on a device with no internet access. Your EMERGENCY answers must be drawn ONLY from the reference passages provided below.

FIRST classify the message:
- EMERGENCY: an injury, illness, symptom, accident, or danger happening now. Follow ALL the emergency rules below.
- GENERAL: prevention, supplies, training, everyday habits (food, drink, coffee, sleep, exercise), or general health knowledge. Answer with a short informative paragraph of 4-8 sentences (or a few bullet points): the key facts, practical amounts and numbers, and one or two useful extras such as what to avoid or when it matters. Never answer a GENERAL question with a single sentence. Do not use the emergency format - no urgent-action opener, no numbered emergency steps, no warning-signs section. For GENERAL questions only: if the reference passages are not relevant to the question, IGNORE them completely and answer from ordinary general knowledge - never force emergency framing into an everyday question (no "in emergency situations" talk unless the user described an emergency). Questions about you ("what can you do", "who are you", "how do you work") get 1-2 sentences describing what you are - an offline first-aid guide that answers emergency questions in Albanian and English - NEVER first-aid instructions, even if the reference passages contain them.

TONE, always: straight to the point and factual. No sympathy lines, no reassurance filler ("stay calm", "I am worried about you"), no apologies, no praise, no exclamation marks, no chit-chat. Every sentence must carry an instruction or a fact.

PERSPECTIVE, always: match who is affected. If the user describes THEIR OWN symptoms ("I feel sick", "my arm is bleeding", "I am dizzy"), speak directly to them as "you" - never about "the person", "him", "her", "the victim" or "the patient". If they describe someone else's emergency, give the user the helper's instructions. NEVER deflect with "find someone to help you", "ask someone else" or "talk to somebody" - the user has only this device; always give the actual steps themselves.

EMERGENCY RULES:
1. Answer ONLY using the reference passages. Never invent facts, procedures, medication names, or doses. If the passages give a specific number, use it exactly.
2. If the passages do not cover the situation, say clearly: "My references don't cover this specific situation." Then give the safest general action and state that professional medical help is needed.
3. Start with the single most urgent action in one short sentence. ONLY IF the question asks whether to do something ("should I...", "can I...", "is it safe to...") begin with "Yes" or "No" and the reason. For any other question do NOT begin with the word "Yes" or "No" - begin directly with the action itself. A prohibition like "Do NOT pull it out" counts as the urgent action.
4. Then give numbered steps in the order they must be done. One action per step. Short sentences. Commands, not suggestions.
5. Use plain language a scared non-expert can follow. Translate medical terms. NEVER drop a "do not" warning from the passages.
6. If the passages contain conflicting advice, prefer the IFRC 2025 guidelines over older sources. Older techniques like induced vomiting for poisoning or loosening tourniquets are outdated - do not recommend them.
7. End by stating when to seek professional medical help and warning signs of worsening.
8. Users may type short, misspelled, panicked fragments. Interpret them charitably. Do not ask clarifying questions unless dangerously ambiguous.
9. If the message suggests the person is unconscious, not breathing, or bleeding heavily, address that first.
10. Do not provide guidance for deliberately harming any person.
11. Never begin with "I'm sorry", "I can't", or "I'm not a medical professional".
12. Two absolute rules: (a) In a severe allergic reaction (face or throat swelling, wheezing after a sting) with an epinephrine auto-injector available, helping the person use it IMMEDIATELY is always correct - never advise waiting for permission. (b) A tourniquet that has been applied must NEVER be loosened or removed outside a medical facility."""

# Small talk answered deterministically - no RAG, no LLM, no MT. A 3B model
# with a context full of emergency passages cannot be trusted to classify
# "how are u" reliably (observed: it fell back to "my references don't cover
# this"). Full-string match only, so real questions are never hijacked.
_ST_SQ = (r"pershendetje|përshëndetje|tungjatjeta|tung|ckemi|ç'?kemi"
          r"|mir[ëe]mbr[ëe]ma|mir[ëe]m[ëe]ngjes\w*|mir[ëe]dita"
          r"|si je(ni)?|si kalon(i)?|a je mir[ëe]|faleminderit|flm|rrofsh"
          r"|kush je( ti)?|[çc]far[ëe] je ti|[çc]far[ëe] di t[ëe] b[ëe]sh|si punon")
_ST_EN = (r"hello|hi|hey|good (morning|evening|afternoon)|how are (you|u)|how r u"
          r"|what'?s up|thank you|thanks|thx|who are (you|u)|what are (you|u)"
          r"|what can (you|u) do|how do (you|u) work")
_ST_FULL = re.compile(r"^(\s*(%s|%s)[\s,!.?]*)+$" % (_ST_SQ, _ST_EN), re.IGNORECASE)


def _smalltalk(q):
    t = (q or "").strip().lower()
    if not t or len(t) > 60 or not _ST_FULL.match(t):
        return None
    sq = bool(re.search(_ST_SQ, t, re.IGNORECASE))
    if re.search(r"kush je|[çc]far[ëe] (je|di)|si punon|who are|what (are|can)|how do", t, re.IGNORECASE):
        return ("Jam NOAH - udhëzues i ndihmës së parë pa internet, në shqip dhe anglisht. "
                "Shkruaj pyetjen e urgjencës dhe shtyp ENTER." if sq else
                "I am NOAH - an offline first-aid guide in Albanian and English. "
                "Type your emergency question and press ENTER.")
    if re.search(r"faleminderit|flm|rrofsh|thank|thx", t, re.IGNORECASE):
        return ("S'ka gjë. Jam këtu nëse të duhet ndihmë." if sq else
                "You're welcome. I'm here if you need help.")
    return ("Mirë. Jam NOAH, udhëzuesi i ndihmës së parë. Shkruaj pyetjen dhe shtyp ENTER."
            if sq else
            "Fine. I am NOAH, the first-aid guide. Type your question and press ENTER.")


# Is the asker talking about someone else, or about themselves?
_OTHER_PERSON = re.compile(
    r"djal|vajz|burr|grua|nus[ëe]|nen[ëe]|bab[ëae]|gjysh|shok|shoqj?[ëe]"
    r"|f[ëe]mij|foshnj|viktim|personi?\b"
    r"|my (son|daughter|husband|wife|mother|father|child|kid|friend|brother"
    r"|sister|baby|grand\w*)|\bhis \b|\bher \b|\bsomeone\b", re.IGNORECASE)
_FIRST_PERSON = re.compile(
    r"\bndihem|m[ëe] dhemb|me dhemb|\bkam \b|\bjam \b|po m[ëe] |u dogja"
    r"|\bme ka\b|\bm[ëe] ka\b|\bi feel|\bi am\b|\bi'?m\b|\bi have\b|\bmy \b"
    r"|u preva|m[ëe] rrjedh|me rrjedh", re.IGNORECASE)

EPD = None
try:
    from eink import EInk
    EPD = EInk()
    print("[e-ink panel active]")
except Exception as e:
    print(f"[e-ink disabled: {e}]")

MT_OK = os.path.isdir("/data/models/nllb-ct2-int8")
print("[translator %s]" % ("ready, lazy-load (shqip)" if MT_OK else "DISABLED - model missing"))

LEDS_OK = True
try:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(LED_SIGNAL, GPIO.OUT)
    GPIO.setup(LED_POWER, GPIO.OUT)
    GPIO.output(LED_POWER, GPIO.HIGH)
except Exception as _e:
    LEDS_OK = False
    print(f"[leds disabled: {_e}]")

blinking = False
def blinker():
    while True:
        if not LEDS_OK:
            time.sleep(1.0); continue
        try:
            if blinking:
                GPIO.output(LED_SIGNAL, GPIO.HIGH); time.sleep(0.25)
                GPIO.output(LED_SIGNAL, GPIO.LOW); time.sleep(0.25)
            else:
                GPIO.output(LED_SIGNAL, GPIO.LOW); time.sleep(0.1)
        except Exception:
            time.sleep(1.0)
threading.Thread(target=blinker, daemon=True).start()

client = chromadb.PersistentClient(path=DB_PATH)
col = client.get_collection("emergency")
retriever = retrieval.Retriever(col)
print("[hybrid retrieval ready: %d chunks]" % len(retriever.docs))

def embed_query(text):
    r = requests.post(f"{OLLAMA}/api/embed",
                      json={"model": "nomic-embed-text", "input": [text]},
                      timeout=(10, 120))
    return r.json()["embeddings"][0]

def answer(question):
    global blinking
    blinking = True
    try:
        st = _smalltalk(question)
        if st:
            return st, []
        is_sq = MT_OK and translator.is_albanian(question)
        q_en = translator.sq_to_en(question) if is_sq else question
        chunks, sources = retriever.search(q_en, k=TOP_K)
        context = "\n\n---\n\n".join(
            f"[Source: {s}]\n{c}" for s, c in zip(sources, chunks))
        # perspective stamp: MT often drops the first person from Albanian
        # ("ndihem semure" -> "feels sick"), so the model answers about "the
        # person". Detect I-the-patient questions deterministically.
        both = (question + " " + q_en).lower()
        note = ""
        if not _OTHER_PERSON.search(both) and _FIRST_PERSON.search(both):
            note = ("\nNOTE: The asker IS the patient. Address them directly "
                    "as 'you' - never 'the person', 'him' or 'her'.")
        prompt = (f"REFERENCE PASSAGES:\n\n{context}\n\n"
                  f"USER QUESTION: {q_en}{note}\n\nANSWER:")
        r = requests.post(f"{OLLAMA}/api/generate", json={
            "model": MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.25, "num_ctx": 3072, "num_predict": 400}
        }, timeout=(10, 300))
        resp = r.json()["response"]
        # degeneration guard: a token loop ("JE JE JE...") is long but garbage -
        # blank it so the short-answer retry below regenerates
        if re.search(r"(\b\w{1,6}\b)(\s+\1\b){7,}", resp):
            resp = ""
        # short-answer guard: one-liners retry once with an expand demand
        # (smalltalk never reaches here - it is answered deterministically)
        if len(resp.strip()) < 180:
            r2 = requests.post(f"{OLLAMA}/api/generate", json={
                "model": MODEL,
                "system": SYSTEM_PROMPT,
                "prompt": prompt + " Answer the question completely and informatively - a single sentence is not enough. If it is an emergency, give the full numbered first aid steps.",
                "stream": False,
                "options": {"temperature": 0.2, "num_ctx": 3072, "num_predict": 400}
            }, timeout=(10, 300))
            resp2 = r2.json().get("response", "")
            if len(resp2.strip()) > len(resp.strip()):
                resp = resp2
        # deterministic guard: strip a leading Yes/No unless the question asked whether
        _modal = re.search(r"\b(should|shall|can|could|may|must) (i|we|you|he|she|they)\b"
                           r"|\bis it (safe|ok|okay|alright)\b", q_en, re.IGNORECASE)
        _wh = re.search(r"\b(what|how|when|where|why|who)\b[^.?!]{0,25}"
                        r"\b(should|shall|can|could|may|must)\b", q_en, re.IGNORECASE)
        if not _modal or _wh:
            m = re.match(r"^(yes|no)[,.:]?\s+", resp.strip(), re.IGNORECASE)
            if m:
                resp = resp.strip()[m.end():]
                if resp:
                    resp = resp[0].upper() + resp[1:]
        names = safety.fired_rules(question, q_en, is_sq)
        resp, replaced = safety.body_guard(names, resp, is_sq)
        if not replaced:
            resp = safety.danger_scrub(resp)   # drop inverted-advice sentences
        med = (not replaced) and safety.med_caution(resp)
        if is_sq and not replaced:
            resp = translator.en_to_sq(resp)
        warns = safety.check(question, q_en, is_sq)
        if warns:
            resp = "\n\n".join(warns) + "\n\n" + resp
        if med:
            resp += "\n\n" + (safety.MED_CAUTION_SQ if is_sq else safety.MED_CAUTION_EN)
        return resp, sorted(set(sources))
    finally:
        blinking = False

def main():
    print("Emergency Assistant ready. Type a question (or 'quit').\n")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q or q.lower() == "quit":
            break
        t0 = time.time()
        text, sources = answer(q)
        dt = time.time() - t0
        print(f"\n{text}\n")
        print(f"[sources: {', '.join(sources)} | {dt:.1f}s]\n")
        if EPD:
            try:
                short = [s.rsplit(".", 1)[0][:40] for s in sources]
                pages = EPD.paginate_text(text, title=q,
                                          footer="sources: " + ", ".join(short))
                EPD.show(pages[0])
                for i in range(1, len(pages)):
                    try:
                        input(f"[panel: page {i}/{len(pages)} shown - Enter for next]")
                    except (EOFError, KeyboardInterrupt):
                        break
                    EPD.show(pages[i])
            except Exception as e:
                print(f"[e-ink error: {e}]")

    if EPD:
        try: EPD.close()
        except Exception: pass
    GPIO.output(LED_POWER, GPIO.LOW)
    GPIO.cleanup()


if __name__ == "__main__":
    main()

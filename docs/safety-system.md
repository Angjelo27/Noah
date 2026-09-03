# The safety system

The heart of NOAH is not the language model - it is the deterministic layer
in [`safety.py`](../software/safety.py) that stands between the model and a
person in an emergency. It was built empirically across **13 adversarial
audit rounds** (hundreds of Albanian and English questions, every failure
fixed and locked with a regression test).

## Layers

1. **50 rules.** Each rule is `(name, english_pattern, albanian_pattern,
   english_warning, albanian_warning)`. Patterns run over both the raw
   question and its translation; a hit prepends a pre-written warning block
   before anything the model says. Coverage includes CPR/not-breathing,
   choking (with an explicit "coughing = don't interfere" clause), stroke
   (incl. folk idioms), poisoning (chemicals, pills, mushrooms, cigarettes,
   button batteries), bleeding, tourniquets, burns (thermal/chemical/sun),
   anaphylaxis, spinal, head injury, seizures, febrile seizures, diabetic
   low AND high sugar, hypothermia, frostbite, heatstroke, heat cramps,
   carbon monoxide, hanging, drowning, chest wounds, amputation, pregnancy
   (bleeding and falls), infants, testicular torsion, eye injuries (blunt
   and chemical), jellyfish, sea urchins, panic attacks, and more.
2. **9 CONTRA bodies.** For failure modes where the model was observed
   *commanding* the forbidden action (loosen the tourniquet, make them
   vomit, Heimlich for a stroke or a nose object), the entire model answer
   is replaced by a pre-written safe answer.
3. **danger_scrub.** Sentence-level deletion of known-dangerous model output
   regardless of context: negated-CPR advice, non-negated "make him vomit",
   "stop the birth", model-initiated tourniquets, "help them stand up"
   after falls, prompt echoes, plus a repetition-loop collapse.
4. **Veto map.** A specific rule silences a contradicting generic one
   (jellyfish ▸ burn - sea water vs fresh water; ketoacidosis ▸ hypoglycemia
   - no sugar vs give sugar; fishbone/nose-object ▸ choking).
5. **Medication caution.** Any answer naming prescription drugs gets a
   bilingual "not without a health worker" line appended.

## The regression matrix

`python3 safety.py` runs an 83-case matrix: real user phrasings (including
dialect, diacritic-free typing, reversed word order, first-person forms)
against expected rule sets, plus scrubber unit tests proving that safe
advice ("do NOT make them vomit") survives while dangerous advice is
deleted. **All changes must keep it at ALL PASS.** The matrix has caught
bugs in its own new rules before deployment more than once.

## Notable catches from the audit rounds

These are real outputs the layers now prevent - kept here as a reminder of
why the floor exists:

- "Loosen the tourniquet to let the blood circulate" (model, 3 of 3 runs)
- Heimlich maneuver for a stroke, a fish bone, and a bean in the nose
- "Do not attempt CPR if the person does not respond" (drowning)
- Glucose tablets for blood sugar 400 with acetone breath
- A tourniquet for an infected wound
- Drowning "float on your back" steps for a panic attack
- EpiPen advice for a heart attack
- Fresh-water rinse for a jellyfish sting
- "The device can't help, find somebody to talk to" for "I feel sick"

## Limits - be honest with users

The layer reduces risk; it cannot eliminate it. The model body under a
correct warning can still be clumsy or off-topic; translations still
produce occasional howlers; and no rule exists for classes nobody has
tested yet. Every transcript in `software/eval/` deserves a professional
medical read - if you build on this, continue the audit loop.

# NOAH software

Everything runs on the Jetson under a single systemd service. Paths assume
user `aldo` with code in `/home/aldo` - either create that user or search
and replace the paths in the `.py` files and service units.

## Components

| File | Role |
|---|---|
| `noah_ui.py` | The device UI: e-ink screens, keyboard input, power-button watcher (suspend / power-off screen), typing refresh, answer pagination. |
| `assistant.py` | Pipeline orchestration: language detect → translate → retrieve → LLM → safety post-processing → translate back. Deterministic small-talk replies. |
| `safety.py` | The deterministic safety layer: 50 bilingual emergency rules, 9 full answer replacements, dangerous-sentence scrubber, rule veto map, medication caution. Self-testing (`python3 safety.py` runs an 83-case matrix). |
| `translator.py` | Albanian↔English via NLLB-200 (CTranslate2 int8), language detection, idiom pre-rewrites, ~150 post-translation corrections. |
| `retrieval.py` | Hybrid retrieval: BM25 + Chroma vectors with reciprocal-rank fusion, query expansions, obsolete-doctrine filter. |
| `eink.py` | IT8951 e-ink driver (SPI + GPIO): 4bpp transfers, partial refresh, controller RAM map, GC16/DU waveforms. |
| `ingest.py` | Builds the vector/BM25 index from the reference PDFs (with a blocklist for outdated medical advice). |
| `recovery_strips.py` | Glass recovery tool: strip-by-strip black/white sweep (run with the service stopped). |
| `system/` | systemd units + logind config. |
| `eval/` | Eval harness + all bilingual question batteries from 13 audit rounds. |
| `tools/` | Controller diagnostics (RAM readback probes). |

## Setup

### 1. Base system

JetPack 6.x (Ubuntu 22.04) on a Jetson Orin Nano 8 GB. Then:

```bash
sudo apt update && sudo apt install -y python3-pip busybox librsvg2-bin
pip3 install chromadb requests pillow numpy rank_bm25 langdetect \
             ctranslate2 transformers sentencepiece Jetson.GPIO spidev
```

### 2. LLM runtime

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

### 3. Translation model (Albanian)

Convert NLLB-200-distilled-600M to CTranslate2 int8 and place it at
`/data/models/nllb-ct2-int8`:

```bash
pip3 install "ctranslate2" "transformers[torch]"
ct2-transformers-converter --model facebook/nllb-200-distilled-600M \
  --output_dir /data/models/nllb-ct2-int8 --quantization int8
```

### 4. Reference library (not included - copyright)

Create `~/emergency-library/` and add:

- **IFRC International First Aid, Resuscitation and Education Guidelines 2025** - ifrc.org
- **WHO Psychological First Aid: Guide for Field Workers** - who.int
- **Where There Is No Doctor** (David Werner) - free from hesperian.org
- **FEMA "Are You Ready?"** - fema.gov (public domain)
- **FM 21-76 US Army Survival Manual** - public domain; trim to the
  medical/survival chapters to keep retrieval focused

Then build the index (stop ollama models you don't need first - ingest is
memory-hungry):

```bash
python3 ingest.py     # → ~/emergency-db (about 4,800 chunks)
```

### 5. Panel driver quirks (read before first boot)

- Set `VCOM_MV` in `eink.py` to YOUR panel's sticker value.
- The pinmux service is mandatory (see `hardware/wiring.md`).
- SPI stays at 4 MHz; the controller stores every frame as 8 bits/pixel
  internally - its 8 MB RAM fits exactly two frames. Do not add parked
  buffers; do not use partial-area displays from parked slots. These limits
  were mapped the hard way; `tools/` contains the probes that proved them.

### 6. Services

```bash
sudo cp system/noah-ui.service system/fix-gpio-pinmux.service /etc/systemd/system/
sudo mkdir -p /etc/systemd/logind.conf.d
sudo cp system/noah-power-logind.conf /etc/systemd/logind.conf.d/
sudo systemctl daemon-reload
sudo systemctl enable --now fix-gpio-pinmux noah-ui
sudo systemctl restart systemd-logind
```

Pair the BB Q10 keyboard once via `bluetoothctl` (`pair` + `trust`).

## Running the eval

```bash
cd eval
python3 sq_eval_runner.py sq_long_questions.txt /tmp/out.txt
```

`safety.py` doubles as a regression test: `python3 safety.py` must print
`ALL PASS` after any rule change. When you find a new failure mode, the
workflow is: add the rule/pattern + a matrix case + re-run the question -
that loop, repeated over 13 audit rounds, is where the safety layer came from.

# NOAH - Offline Emergency First-Aid Terminal

**by American Labs · [american.al](https://american.al)**

NOAH is a fully offline, battery-friendly field terminal that answers emergency
first-aid questions in **Albanian and English**. It runs a local LLM with
retrieval over trusted first-aid references on an NVIDIA Jetson Orin Nano,
displays on a 7.8" e-ink panel, and takes input from a pocket keyboard. No
internet, no cloud, no account - press the button, type the question, get the
steps.

![NOAH prototype](docs/images/device-prototype.jpg)

## Why

In an emergency without connectivity - mountains, blackouts, disasters - the
knowledge in books like *Where There Is No Doctor* is life-saving but hard to
search when your hands are shaking. NOAH turns that library into a device you
can ask in your own words, in the language you panic in.

## What it does

- **Ask in Albanian or English**, typed on a small Bluetooth keyboard; language
  is detected automatically and answers come back in the language you asked in.
- **Grounded answers**: a local llama3.2:3b answers strictly from retrieved
  passages of bundled first-aid references (IFRC 2025, WHO PFA, Werner, FEMA,
  FM 21-76 survival manual) - ~4,800 indexed chunks.
- **A deterministic safety layer above the model**: 50 keyword-triggered
  emergency rules with pre-written bilingual warnings (CPR, choking, stroke,
  poisoning, button batteries, ketoacidosis, hanging, chemical eye burns…),
  9 full answer replacements for known model failure modes, a scrubber that
  deletes dangerous model sentences (e.g. "make him vomit", "apply a
  tourniquet"), and a veto system so specific rules silence contradicting
  generic ones. Built and hardened across 13 adversarial audit rounds.
- **E-ink UI** designed for the field: word-at-a-time typing refresh,
  full-screen self-healing repaints, silent suspend on a short button press,
  and a persistent "POWERED OFF" screen (e-ink keeps its image with no power).
- **Runs cold**: boot to ready ≈ 60 s; wake from suspend ≈ 3 s with the model
  still warm; English answers in ~7-18 s, Albanian ~25-40 s (translation
  sandwich via NLLB-200).

## Repository layout

| Folder | Contents |
|---|---|
| [`software/`](software/) | All device code (UI, pipeline, safety layer, driver), systemd units, eval harness. Setup guide in its README. |
| [`hardware/`](hardware/) | [Bill of materials](hardware/BOM.md), [wiring guide](hardware/wiring.md), [assembly notes](hardware/assembly.md). |
| [`3d-models/`](3d-models/) | Printable STLs for the full enclosure (shell, visor, plates, bumpers, fit-test coupons) + the Blender source. |
| [`docs/`](docs/) | [Architecture](docs/architecture.md) and the [safety system](docs/safety-system.md) in detail. |

## Quick start

1. Print the enclosure - see [`3d-models/README.md`](3d-models/README.md).
2. Buy the parts - see [`hardware/BOM.md`](hardware/BOM.md).
3. Wire the panel, button and LEDs - see [`hardware/wiring.md`](hardware/wiring.md).
4. Flash JetPack and install the software - see [`software/README.md`](software/README.md).

## ⚠️ Disclaimer

**NOAH is an experimental, educational DIY project - it is not a medical
device and has not been reviewed or certified by any medical authority.**
Its answers come from a small language model constrained by a hand-built
safety layer; errors, mistranslations and omissions are possible and have
been observed during development. It must never replace professional medical
care, emergency services, or first-aid training. If you build one, have its
output reviewed by a medical professional, and treat it as a backup for
situations where no better help is available. The authors accept no
liability for its use.

The first-aid reference texts are **not** included in this repository for
copyright reasons; the software README lists where to obtain each one.

## License

Code and 3D models: [MIT](LICENSE). The NOAH name and logo belong to
American Labs.

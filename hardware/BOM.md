# Bill of Materials

| # | Part | Details | Qty |
|---|------|---------|-----|
| 1 | **NVIDIA Jetson Orin Nano 8 GB Developer Kit** | The brain. Runs the LLM, translation and retrieval. NVMe SSD strongly recommended (models + index ≈ 10 GB). | 1 |
| 2 | **Waveshare 7.8" e-Paper HAT (B)** | IT8951 controller, 1872 × 1404, 16 grey levels. Panel + driver board + adapter. | 1 |
| 3 | **BB Q10 Bluetooth keyboard module** | BlackBerry Q10 keyboard with a Bluetooth controller board (sold as a DIY module). Pairs as a standard BT HID keyboard. | 1 |
| 4 | **USB-C PD power supply, 65 W with a 15 V profile** | ⚠️ See the power warning in [wiring.md](wiring.md) - cable choice matters. | 1 |
| 5 | **Momentary push button** | Panel-mount, normally-open. Wired to the Jetson's button header: suspend / wake / power-off / power-on. | 1 |
| 6 | **LEDs, 3 mm/5 mm + series resistors (≈330 Ω)** | Power LED and signal ("thinking") LED, front panel via the printed lens. | 2 |
| 7 | **Dupont jumper wires, female-female** | Panel SPI + power harness (10+), button, LEDs. For the permanent build, replace with a soldered harness. | ~20 |
| 8 | **Neodymium disc magnets** | Hold the screen visor to the shell (design uses 7). Size per the pockets in the printed parts - verify with `NOAH_FitCoupon_Magnet.stl` before committing. | 7 |
| 9 | *(Optional)* **Small solar panel** | The shell has integrated solar mounting tabs + printed tab locks. Any thin panel that fits the back recess; feeds a USB power bank, not the Jetson directly. | 1 |
| 10 | *(Optional)* **USB power bank, USB-C PD, 15 V capable** | For true field use. ⚠️ Read the 20 V cable warning in wiring.md **before** battery use. | 1 |

## Print-side consumables

- PETG (or PLA for indoor units) for the shell, visor, plates - see
  [`3d-models/README.md`](../3d-models/README.md).
- TPU for the rubber bumpers (`bumpers/`, `NOAH_RubberBumpers.stl`).
- M2/M3 screws per the boss holes in the shell (verify against your print).

## Tools

- Multimeter - genuinely required once: for continuity checks before the 5 V
  harness reinforcement and for **identifying safe charging cables** (see the
  20 V warning). A cheap one is fine.
- Soldering iron for the permanent harness (the prototype runs on dupont).

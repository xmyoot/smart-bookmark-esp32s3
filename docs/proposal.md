# Proposal — smart bookmark PCB + firmware

> **Before sending:** fill the two `[[ ... ]]` name fields, and read the note at the bottom about
> the hours. Everything technical here is backed by the files in this folder.

---

Hi [[client name]],

Rather than describe how I would approach your bookmark, I went ahead and did the design work, so
you can judge the result instead of a promise. As of today I have:

- a complete schematic for your product, with every part chosen and in stock at JLCPCB,
- a routed 37 x 52 mm board that passes design-rule checks, with Gerbers, BOM and
  pick-and-place files generated,
- firmware in C (ESP-IDF) that compiles: hold-to-record, clip storage, BLE transfer, battery
  reporting, LED states and deep sleep,
- a written BLE protocol for your app developer.

That is why the price and timeline below are far smaller than you will see in other bids: most
of the hours are already spent, and I am not charging for them. What is left is fitting the
board to your enclosure, building it, and proving it on real hardware.

## What the design is

- **ESP32-S3-MINI-1 module.** It keeps your working ESP32-S3 firmware base and the S3's hardware
  PDM microphone interface, is 2.4 mm tall, and has a pre-certified antenna. Your button and LED
  stay on the same pins as your XIAO prototype.
- **No SD card.** Clips are stored as compressed audio (a quarter the size of raw audio, so
  Bluetooth sync is four times faster) on a 16 MB flash chip: about 40 minutes of recordings
  between syncs.
- **Thin LiPo, USB-C charging, on-board cell protection**, charge current matched to a small
  cell, battery level read through a divider that is switched off in sleep.
- **About 15 µA in deep sleep** by the datasheet figures, which is months of standby on a
  150 mAh cell. Real use is what drains it: roughly six weeks at ten 20-second clips a day.
- **Assembly on one side only**, 4-layer 0.8 mm board, programming and test pads on the back.
- **Firmware laid out for over-the-air updates** later, through your app.

## Milestones and fixed price

Rate: **US$25 per hour**. Each milestone is a fixed price; if it takes me longer, that is my cost.

| # | Milestone | You receive | Hours | Price | When |
|---|---|---|---|---|---|
| 1 | Schematic and component selection | Schematic PDF and KiCad source, BOM with JLCPCB part numbers, design notes. One round of your changes | 3 | US$75 | Day 1 |
| 2 | PCB layout | Board fitted to your enclosure CAD (connector, button and microphone positions), 3D STEP file, Gerbers, BOM and pick-and-place for JLCPCB | 5 | US$125 | Days 2–3, after I have the enclosure CAD |
| 3 | Firmware and BLE protocol | Source code, build instructions, protocol document | 6 | US$150 | Days 2–4 |
| 4 | Working boards | First boards powered up and tested: charging, sleep current, a recorded clip pulled over Bluetooth; test report and any firmware fixes found on hardware | 10 | US$250 | 2–3 days after the boards arrive |
| | **Total** | | **24** | **US$600** | |

**Timeline.** My work for milestones 1 to 3 is done within four working days of receiving your
enclosure CAD. Milestone 4 depends on the factory: JLCPCB typically takes one to two weeks to
build and ship assembled boards, and nobody can shorten that except by paying for faster
shipping. I finish testing within three days of the boards reaching me.

**Not included:** the boards and parts themselves (ordered on your JLCPCB account or billed at
cost, quoted before ordering), batteries, shipping, certification testing, and the phone app.
If the first boards show a hardware fault that needs a second board revision, I correct the
design at no charge; the second batch of boards is at cost.

You own all source files (schematic, PCB, Gerbers, BOM, firmware) on payment of each milestone.

## Your three questions

**1. Have you built BLE products on the ESP32-S3?**

My directly relevant work is on the ESP32 family rather than a shipped ESP32-S3 BLE product, and I
would rather say that plainly:

- An **ESP32-C6 coin-cell BLE sensor** for a buried, potted industrial application: 31.5 mm round
  board, CR2450 cell. I did the power architecture and design specification, including the radio
  current budget (the BLE transmit current turned out to be 131 mA, not the 80–90 mA originally
  assumed, which changed the whole supply design).
- An **ESP32 Wi-Fi controller** (plant watering): schematic through to a complete, rule-checked
  KiCad project for JLCPCB assembly.
- **This design**: the ESP32-S3 BLE firmware for your bookmark is written and compiles, with a
  documented transfer protocol (clip list, chunked download with resume and CRC, pairing and
  encryption). It has not yet run on hardware, because no board exists yet. That is milestone 4.

**2. Have you designed small, battery-powered or wearable devices with LiPo charging?**

- The coin-cell sensor above was an exercise in exactly this: nanoamp-level regulator choice,
  cold-start behaviour, and fitting cell, antenna and connector in a 31.5 mm circle.
- An **ESP32-P4 camera** with single-cell Li-ion charging and protection, where I specified the
  charger, battery-temperature cutoff and the load switching that decides battery life.
- For your board I selected and laid out the charger, cell protection, a 2 µA regulator and a
  battery-sense circuit that draws nothing in sleep, and budgeted the standby current part by
  part. Measuring that budget on the first boards is part of milestone 4.

**3. Concerns and suggestions for a first run of about 500 units**

1. **Enclosure first.** The board fits 37 x 52 mm easily; height is the tight dimension. A 0.8 mm
   board, 2.4 mm module and 2.5 mm cell stack to 5.7 mm, and the USB-C connector is 3.3 mm tall on
   its own. I need the enclosure CAD to confirm the interior height and to put the USB opening,
   button and microphone hole where your case has them.
2. **Microphone acoustics.** A MEMS microphone needs a short, sealed path to the outside. The
   hole position, a gasket and a dust mesh belong in the enclosure design now; they are the most
   common reason a good board sounds bad in its case.
3. **Battery.** Buy cells with test reports (UN38.3, IEC 62133) from the start: you need them to
   ship the product. The board has its own protection circuit and charges gently, but the cell
   you choose also sets one resistor value on the board.
4. **Radio certification.** A pre-certified module means FCC and CE testing covers unintentional
   emissions and the battery, not a full radio approval. That saves real money and weeks.
5. **Production test.** At 500 units you want a simple pogo-pin jig and a five-second self-test
   (microphone, button, LED, battery reading, radio). The test pads are already on the board;
   the jig and test firmware are a small follow-on job.
6. **Start-up delay.** Waking from deep sleep takes a few tenths of a second, so the first
   syllable after a press can be lost. The LED comes on when recording has really started.
   If "press, wait for the light, speak" is not acceptable, there are options at some cost in
   standby current.
7. **Parts supply.** Everything is in stock at JLCPCB today. I would still reserve the module
   and the microphone for the full 500 at the prototype stage, since those two set the schedule.
8. **Updates in the field.** Add over-the-air updates through your app before the Kickstarter
   units ship. The firmware layout already leaves room for it.

I am interested in the follow-on work too: production support, the test jig and later revisions,
at the same rate.

[[your name]]

---

## Note to self (delete before sending)

- **24 hours is tight.** It assumes the enclosure needs only connector, button and mic moves and
  that the first boards work. Bring-up is where hours usually overrun; at a fixed US$250 for
  milestone 4, a stubborn fault comes out of your own time. The free design correction for a
  second revision is a real commitment.
- **Milestone 3 says the firmware is delivered in days**, which is true for source code. It only
  becomes *tested* firmware in milestone 4.
- The experience answers cite the coin-cell sensor and the P4 camera as design/specification
  work, which is what they were. Neither names its client.
- "A few days" is honest only for your own work; the proposal says so and puts the factory lead
  time on JLCPCB.

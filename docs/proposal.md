# Proposal draft — smart bookmark PCB + firmware

> **Before sending:** fill every `[[ ... ]]`. Prices, dates and your own project examples are
> yours to state; nothing here was invented for them. The technical content is backed by the
> design files in this folder.

---

Hi [[client name]],

I read your brief closely and, to show how I would approach it rather than describe it, I have
already worked the design through to a complete schematic, a first board placement at your
37 x 52 mm size, and a draft of the firmware and BLE protocol. A summary is below; I am glad to
share the files on a call.

## What I would build

- **ESP32-S3-MINI-1-N8 module.** It keeps your working ESP32-S3 firmware base and the S3's
  hardware PDM microphone interface, and it is 2.4 mm tall with a pre-certified antenna. I looked
  at the ESP32-C6 and nRF52840: the C6 cannot decode a PDM microphone in hardware, and the nRF
  would mean rewriting firmware you already have working.
- **No SD card.** Clips go to the module's own flash as compressed audio (ADPCM, a quarter the
  size of raw audio, which also makes Bluetooth sync four times faster). That removes the tallest
  and most power-hungry part of the prototype. A 16 MB flash chip on the board
  gives about 40 minutes of backlog between syncs.
- **Thin LiPo, USB-C charging, on-board cell protection**, charge current matched to a small cell,
  and battery level read through a divider that is switched off in sleep.
- **About 15 µA in deep sleep** by the datasheet figures: module 8, regulator 2, protection 3, flash 1.
  That is months of standby on a 150 mAh cell, so in practice the cell's own self-discharge is
  the limit. Active use is what drains it: roughly six weeks at ten 20-second clips a day.
- **Single-sided assembly, every part in stock at JLCPCB**, 4-layer 0.8 mm board, programming
  and test pads on the back for a production jig.
- **Firmware in ESP-IDF (C):** hold-to-record, clips stored with timestamps, BLE transfer with
  resume and CRC, pairing and encryption, battery reporting, LED states, deep sleep, and
  partitions laid out for over-the-air updates later.
- **A written BLE protocol** for your app developer: service and characteristic UUIDs, message
  formats, the download sequence, and the audio file format.

## Milestones and fixed price

| # | Milestone | You receive | Price | Duration |
|---|---|---|---|---|
| 1 | Schematic and component selection | Schematic PDF + KiCad source, BOM with JLCPCB part numbers, design notes; your review and sign-off | [[price]] | [[e.g. 1 week]] |
| 2 | PCB layout | KiCad board, 3D STEP for your enclosure check, Gerbers, BOM and pick-and-place for JLCPCB; placement review with you before routing | [[price]] | [[e.g. 1.5 weeks]] |
| 3 | Working boards | First batch ordered (5–10 boards), bring-up, power and sleep-current measurements, audio check, test report | [[price]] | [[e.g. 3 weeks incl. fabrication and shipping]] |
| 4 | Firmware and BLE protocol | Source code, build instructions, protocol document, a short demo of record → sync against a test app | [[price]] | [[e.g. 2 weeks, overlapping milestone 3]] |
| | **Total** | | **[[total]]** | **[[about 6–7 weeks]]** |

Not included in the fixed price: board fabrication and parts ([[estimate, e.g. about US$X for 10
assembled boards]]), batteries, shipping, certification testing, and the phone app. You own all
source files (schematic, PCB, Gerbers, BOM, firmware) on payment of each milestone.

## Your three questions

**1. Have you built BLE products on the ESP32-S3?**

[[Your answer and one concrete example: what the product was, what the BLE link carried, what
went to production. If your closest example is another ESP32 variant or another BLE chip, say
that plainly.]]

**2. Have you designed small, battery-powered or wearable devices with LiPo charging?**

[[Your answer and example: cell size, charger used, measured standby current if you have it.]]

**3. Concerns and suggestions for a first run of about 500 units**

1. **Enclosure first.** The board is easy to fit in 37 x 52 mm; the height is the tight
   dimension. With a 0.8 mm board, a 2.4 mm module and a 2.5 mm cell the stack is 5.7 mm, and
   the USB-C connector is 3.3 mm tall on its own. I would like the enclosure CAD before layout is
   frozen, mainly for the interior height and the positions of the USB opening, the button and
   the microphone hole.
2. **Microphone acoustics.** A MEMS microphone needs a short, sealed path to the outside. The
   hole position, a gasket and a dust mesh belong in the enclosure design now; they are the most
   common reason a good board sounds bad in its case.
3. **Battery.** Buy cells with test reports (UN38.3, IEC 62133) from the start: you need them to
   ship the product and for Kickstarter fulfilment. The board has its own protection circuit
   and charges gently, but the cell choice also sets the charge-current resistor.
4. **Radio certification.** Using a pre-certified module means FCC and CE testing covers
   unintentional emissions and the battery, not a full radio approval. That saves real money
   and weeks. A bare-chip design would be thinner but loses this, so I would keep it for a later
   revision.
5. **Production test and programming.** At 500 units you want a simple bed-of-nails jig and a
   five-second self-test (microphone, button, LED, battery reading, radio). The test pads are on
   the board already; the jig and test firmware are a small follow-on job.
6. **Storage.** The board holds about 40 minutes of audio between syncs (16 MB flash chip). If
   your users may go weeks without opening the app, a larger NAND part fits the same interface.
7. **Start-up delay.** Waking from deep sleep takes a few tenths of a second, so the first
   syllable after a press can be lost. The LED comes on when recording has really started; a
   "press, wait for the light, speak" habit covers it. If that is not acceptable there are
   options, at some cost in standby current.
8. **Parts supply.** Everything is stocked at JLCPCB today; I would still buy the module and the
   microphone for the full 500 at the prototype stage, since those two decide the schedule.
9. **Updates in the field.** The firmware layout leaves room for over-the-air updates through
   your app. I recommend adding that before the Kickstarter units ship.

I am interested in the follow-on work as well: production support, the test jig and later
revisions.

[[your name / sign-off]]

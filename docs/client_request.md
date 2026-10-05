# Client request — smart bookmark voice recorder

Received 2026-10-05. The text under "Request as written" is the client's own wording, unchanged.
Everything after it is ours.

## Request as written

**Custom compact PCB + firmware from working ESP32-S3 prototype (BLE, audio, LiPo)**

Summary
a smart bookmark for physical books. You press a button, speak a thought, and the recording syncs
to a phone app where it's transcribed and organized by book. I have a working breadboard prototype
and need an experienced engineer to turn it into a compact, manufacturable custom PCB with
production-ready firmware.

Current working prototype:
- Seeed XIAO ESP32-S3
- Push button on D0 to GND (internal pull-up)
- Status LED on D1 through a ~220 ohm resistor
- PDM microphone for voice recording
- SD card for storing audio clips (open to replacing with onboard flash)
- Firmware that records audio on button press

What the final board needs:
- Very thin, small form factor to fit a bookmark-shaped enclosure (approx. 37 x 52 mm board area
  inside a 40 x 55 x 8 mm head; enclosure CAD available)
- ESP32-S3 (or recommended alternative) with Bluetooth Low Energy to transfer audio clips to a
  phone app
- Thin LiPo battery with USB-C charging and battery-level monitoring
- Low-power design: deep sleep between uses, with standby battery life measured in weeks
- Designed for assembly at JLCPCB

Deliverables:
1. Schematic and component selection
2. PCB layout (full source project files)
3. Gerbers, BOM, and pick-and-place files ready for JLCPCB
4. Bring-up and testing of the first prototype boards
5. Firmware source code (C/C++): button handling, audio recording, storage, BLE transfer, power
   management, LED status
6. Brief documentation of the BLE transfer protocol so I can connect it to my phone app

I must receive and own all source files (schematic, PCB project, Gerbers, BOM, and firmware code).

Please quote a fixed price broken into milestones (schematic, layout, working boards, firmware),
with an estimated timeline.

In your proposal, please answer:
1. Have you built BLE products on the ESP32-S3? Please share an example.
2. Have you designed small, battery-powered or wearable devices with LiPo charging?
3. Any concerns or suggestions about this design for a first production run of around 500 units?

This is the first step toward a Kickstarter launch, so there may be ongoing work for production
support and future revisions.

## Open questions for the client

Each has the assumption the current design is built on. A different answer to Q1–Q5 moves parts
on the board; the rest change values or firmware only.

| # | Question | Assumption in the design now |
|---|---|---|
| Q1 | Please send the enclosure CAD. What is the clear interior height of the head, and where are the walls, bosses and snap features? | 6.0 mm clear interior, flat floor, no bosses inside the 37 x 52 mm board area |
| Q2 | Which edge of the head does the bookmark tail attach to, and where should the USB-C opening be? | Tail leaves the bottom short edge. USB-C is on the right long edge, 10.5 mm up from the bottom corner, shell overhanging the board edge by 1.0 mm |
| Q3 | Where is the button on the face, and is it a flexing skin or a separate cap? | Centre line of the board, 31.5 mm from the antenna end; 2.0 mm tall tactile switch |
| Q4 | Where does sound enter? | A hole in the back face. The mic is a bottom-port part on the top side, so sound comes through a 0.5 mm hole in the PCB at x 33.2, y 26.7 mm |
| Q5 | Which cell (or what capacity and maximum thickness)? Does it carry its own protection board? | 25 x 30 x 2.5 mm pouch cell, about 150–200 mAh, fixed to the bare back of the board, wires to two solder pads. Board has its own protection and charges at 100 mA |
| Q6 | How long is a typical clip, and how many must the bookmark hold before it next meets the phone? | Clips under one minute; a 16 MB flash chip is fitted, giving about 40 minutes of total backlog once the firmware uses it (about 8 minutes on the module's own flash until then) |
| Q7 | Where should the LED show, and what colour? | One red LED, top-left of the face, next to the module |
| Q8 | iOS, Android, or both? Does the app need to sync in the background? | Both; app connects when the user opens it, or within 30 s of a recording |
| Q9 | Which markets and certifications for the Kickstarter (FCC, CE, UKCA, others)? | FCC and CE. A pre-certified module is used so the radio certification can be leveraged |
| Q10 | Can you share the prototype firmware and the PDM microphone part number? | Not needed to proceed; useful to match audio level and sample rate |
| Q11 | Any need for audible or haptic feedback when recording starts? | None; LED only |

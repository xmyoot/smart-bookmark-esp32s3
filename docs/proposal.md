Hello,

I've already done the core design work for your bookmark, so you can judge the result instead of a promise. I'm a US-based electrical engineer (BS in EE, Pacific time) with strong written English, so you'll get clear updates and quick replies.

Here's what exists today:

I have a complete schematic with every part in stock at JLCPCB, and a routed 37 x 52 mm board that passes DRC, with Gerbers, BOM and pick-and-place files ready. I also have ESP32-S3 firmware that compiles, covering hold-to-record, clip storage, BLE transfer, battery reporting and deep sleep, plus BLE protocol documentation for your mobile developer.

Price: $49 flat for the whole project. You pay $25 when I deliver the schematic, BOM, the PCB fitted to your enclosure CAD, and the firmware and protocol docs. You pay the remaining $24 once the first boards are tested on hardware (charging, sleep current, and a recorded clip pulled over Bluetooth). This is a passion project for me, which is why the price is so low.

Revisions and board respins are unlimited at no extra charge until you have a working board. Boards, parts, batteries, shipping, certification and the phone app aren't included, and any additional board batches are billed at cost. You own all files as each payment is made.

Timeline: the first three deliverables are done within 4 working days of receiving your enclosure CAD. JLCPCB build and shipping usually takes 1 to 2 weeks, and I finish testing within 3 days of the boards arriving.

Experience: I've done ESP32-family BLE and battery-powered work, including a coin-cell BLE sensor and a LiPo-charged camera. This is my first ESP32-S3 BLE design, and the firmware hasn't run on hardware yet. That's what the final stage is for.

For your 500-unit run: send me the enclosure CAD first, since height is the tight dimension. Plan the mic hole, gasket and dust mesh into the case now. Buy cells with UN38.3 and IEC 62133 test reports, and reserve the module and mic for the full 500. Also expect a short wake-up delay, so users should wait for the LED before speaking.

I'm happy to help with production support and the test jig too, quoted separately.

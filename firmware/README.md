# Smart bookmark firmware

ESP-IDF (v5.3 or newer) project for the Rev A board. C, NimBLE, LittleFS.

## Build and flash

```
idf.py set-target esp32s3
idf.py build
idf.py -p <port> flash monitor
```

The board enumerates over its USB-C port (native USB-Serial-JTAG), so no adapter is needed.
On a blank module, or if the port does not appear, hold the BOOT pad (TP4) to GND while
plugging in USB. `platformio.ini` is provided as an alternative (`pio run -t upload`).

## Behaviour

| Action | Result |
|---|---|
| Hold the button | LED on once recording has started; records until release (max 120 s) |
| Release | Clip saved; LED blinks briefly every 2 s while the phone can connect (30 s) |
| Tap the button (under 0.4 s) | Nothing recorded; the 30 s connect window opens |
| Phone connected | LED blinks fast; clips are transferred; sleeps 20 s after the last traffic |
| Plug in USB | Connect window opens for 60 s; charging runs on its own |
| 3 flashes on press | Battery too low to record |
| 5 flashes | Storage full: sync to free space |
| 8 flashes | Microphone or storage fault |

## Source map

| File | Role |
|---|---|
| `main/board.h` | Pin map and all tunable constants |
| `main/app_main.c` | Wake, record, serve the phone, sleep |
| `main/audio.c` | PDM microphone capture, DC removal, gain |
| `main/adpcm.c` | IMA ADPCM encoder (WAV-compatible 256-byte blocks) |
| `main/clip_store.c` | Clip files on the LittleFS partition |
| `main/ble_xfer.c` | BLE service; protocol in `../docs/ble_protocol.md` |
| `main/power.c` | Battery reading, USB / charger status, deep sleep |
| `main/led.c` | LED patterns |
| `partitions.csv` | 2 x 1.75 MB app slots (OTA-ready), 4.4 MB clip storage |

## Status

Written against the Rev A schematic. **Not yet run on hardware** (no boards exist yet); see
`../docs/testing.md` for the bring-up order and the items to tune on the first article
(microphone slot and gain, battery calibration, sleep current).

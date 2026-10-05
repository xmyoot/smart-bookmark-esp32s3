# Smart bookmark — BLE clip transfer protocol, version 1

For the phone app developer. The firmware side is `firmware/main/ble_xfer.c`; the constants
below are the same ones in that file.

## 1. Overview

The bookmark is a BLE peripheral. It is asleep almost all the time and is only visible:

- for 30 s after the button is released (after a recording, or a short tap to "sync now"),
- for 60 s after USB is plugged in.

The app scans for the service UUID, connects, pairs on first use, asks for the clip list,
downloads each clip, checks its CRC, then deletes it from the bookmark. If the app sends nothing
for 20 s the bookmark disconnects and goes back to sleep.

## 2. Advertising

| Field | Value |
|---|---|
| Advertising data | Flags, complete list of 128-bit service UUIDs (the bookmark service) |
| Scan response | Complete local name `Bookmark-XXXX` (last two bytes of the BLE address, hex) |
| Interval | 100–150 ms, connectable, general discoverable |

## 3. GATT

| Item | UUID | Properties |
|---|---|---|
| Bookmark service | `b00c0001-6e2f-4c1a-9d3e-7a5b10f0c0de` | |
| Control | `b00c0002-6e2f-4c1a-9d3e-7a5b10f0c0de` | Write (with response, encrypted link required), Notify |
| Data | `b00c0003-6e2f-4c1a-9d3e-7a5b10f0c0de` | Notify |
| Battery service | `0x180F` | |
| Battery level | `0x2A19` | Read, Notify (0–100 %) |

Writing to Control on an unencrypted link returns *Insufficient Authentication*. iOS and Android
both respond by pairing automatically ("Just Works", LE Secure Connections, bonded). No PIN.

After connecting, the app should:

1. Request MTU 247 (Android: `requestMtu(247)`; iOS negotiates by itself).
2. Enable notifications on **Control** and **Data** (write `0x0001` to each CCCD).
3. Android only: `requestConnectionPriority(CONNECTION_PRIORITY_HIGH)` during a download.

The bookmark itself asks for a 15–30 ms connection interval, 251-byte packets and the 2M PHY.

## 4. Messages

All integers are little-endian. Every message starts with a one-byte opcode.

### Commands: app writes to Control

| Opcode | Name | Payload after the opcode | Reply on Control |
|---|---|---|---|
| `0x01` | GET_INFO | — | INFO |
| `0x02` | LIST | — | LIST_ENTRY for each clip, then LIST_END |
| `0x03` | READ | `clip_id` u32, `offset` u32 | Data notifications, then READ_DONE |
| `0x04` | ABORT | — | The running LIST or READ ends with ERROR (ABORTED) |
| `0x05` | DELETE | `clip_id` u32 | DELETED |
| `0x06` | SET_TIME | `unix_seconds` u32 (UTC) | TIME_SET |

One command at a time: a second command while LIST or READ is running gets ERROR (BUSY).
ABORT is the exception.

### Replies: bookmark notifies on Control

| Opcode | Name | Payload after the opcode |
|---|---|---|
| `0x81` | INFO | `protocol` u8 (=1), `fw_major` u8, `fw_minor` u8, `codec` u8 (1 = IMA ADPCM), `sample_rate` u16, `block_bytes` u16 (=256), `clip_count` u16, `storage_total` u32 bytes, `storage_used` u32 bytes, `battery_mv` u16, `flags` u8 (bit 0 USB present, bit 1 charging) |
| `0x82` | LIST_ENTRY | `clip_id` u32, `size` u32 bytes, `timestamp` u32, `duration_ms` u32 |
| `0x83` | LIST_END | `count` u16 |
| `0x84` | READ_DONE | `clip_id` u32, `size` u32, `crc32` u32 |
| `0x85` | DELETED | `clip_id` u32 |
| `0x86` | TIME_SET | — |
| `0xFF` | ERROR | `opcode` u8 (the command that failed), `code` u8 |

Error codes: 1 unknown opcode, 2 bad length, 3 no such clip, 4 bad offset, 5 busy, 6 aborted,
7 storage read error.

### Clip bytes: bookmark notifies on Data

Each notification is `offset` u32 followed by clip bytes. `offset` is the position of the first
byte in the file. Packets arrive in order with no gaps; the payload length is whatever fits the
MTU (up to 240 bytes at MTU 247). Write each payload at its offset.

## 5. Downloading a clip

```
App                                   Bookmark
 │  Control: 02                         │   LIST
 │◄─ Control: 82 id size time dur ──────│   one per clip, oldest first
 │◄─ Control: 83 count ─────────────────│
 │  Control: 03 id 00000000 ───────────►│   READ from the start
 │◄─ Data: offset + bytes  (many) ──────│
 │◄─ Control: 84 id size crc32 ─────────│
 │   check size and CRC                 │
 │  Control: 05 id ────────────────────►│   DELETE only after the clip is safely stored
 │◄─ Control: 85 id ────────────────────│
```

- **CRC:** standard CRC-32 (IEEE 802.3, the same as zlib `crc32()`), over the **whole file from
  byte 0**, whatever offset the READ started at.
- **Resume:** if the link drops mid-clip, reconnect and READ with `offset` = number of bytes
  already stored. The CRC in READ_DONE still covers the whole file, so check it against all
  the bytes you hold.
- **Clip ids** only ever increase and are never reused, even after deletion. Use them to
  recognise a clip you already downloaded but failed to delete.
- **Time:** the bookmark has no battery-backed clock. Send SET_TIME on every connection. Clips
  recorded before the first SET_TIME after a full power loss have `timestamp` = 0; fall back
  to the download time and clip order.
- Expect roughly 20–60 kB/s depending on the phone. A 20-second clip is 160 kB.

## 6. Clip file format

The bytes you download are a complete file:

| Offset | Size | Field |
|---|---|---|
| 0 | 4 | Magic, ASCII `BMK1` |
| 4 | 1 | Header version, 1 |
| 5 | 1 | Codec, 1 = IMA ADPCM mono |
| 6 | 2 | Sample rate in Hz (16000) |
| 8 | 4 | Timestamp, Unix seconds, 0 if unknown |
| 12 | 4 | Number of PCM samples in the clip |
| 16 | … | Audio: a whole number of 256-byte IMA ADPCM blocks |

Each 256-byte block is exactly a mono block of Microsoft IMA ADPCM (WAV format tag `0x0011`):
bytes 0–1 first sample (int16), byte 2 step index, byte 3 zero, then 252 bytes of 4-bit codes,
low nibble first. One block decodes to 505 samples. The last block is padded; use the sample
count in the header to trim.

To get a playable file without decoding, write a WAV header in front of the audio bytes with:
format tag `0x0011`, 1 channel, 16000 Hz, 8110 bytes/s average, block align 256, 4 bits per
sample, extra size 2, samples per block 505, plus a `fact` chunk holding the sample count.
Most speech-to-text services accept that file directly; otherwise decode to 16-bit PCM first
(the decoder is about 30 lines in any language).

## 7. Security notes

- Commands need a bonded, encrypted link, so a stranger's phone cannot list, read or delete
  clips. The first pairing is "Just Works": it is not protected against an attacker who is
  present during that first pairing. That is the usual trade-off for a device with no screen.
- To pair a new phone when the old bond is gone, "forget" the bookmark in the phone's Bluetooth
  settings and connect again; the bookmark drops its stale bond automatically.
- Setting `BLE_REQUIRE_ENCRYPTION` to 0 in `board.h` removes the pairing requirement, which is
  convenient while the app is being developed.

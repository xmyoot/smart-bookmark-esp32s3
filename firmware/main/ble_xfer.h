/* BLE clip transfer service (NimBLE peripheral). Protocol: docs/ble_protocol.md. */
#pragma once

#include <stdbool.h>
#include <stdint.h>

/* Start the BLE host and the transfer task. Call once. */
void ble_xfer_start(void);

/* (Re)start advertising for the given time. Ignored while a phone is connected. */
void ble_xfer_advertise(int seconds);

bool ble_xfer_connected(void);
bool ble_xfer_advertising(void);

/* Milliseconds since the phone last wrote a command or received data. */
uint32_t ble_xfer_idle_ms(void);

void ble_xfer_set_battery(uint8_t percent, uint16_t millivolts);

/* Battery measurement, USB / charger status and deep sleep. */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void power_init(void);

bool power_button_down(void);
bool power_usb_present(void);
bool power_charging(void);

/* Connects the divider, reads the cell voltage in mV, disconnects it again. Takes about 35 ms. */
int power_battery_mv(void);
uint8_t power_battery_percent(int mv);

/* Arms wake on the button (and on USB plug-in when USB is absent) and never returns. */
void power_deep_sleep(void) __attribute__((noreturn));

/* Status LED patterns. */
#pragma once

typedef enum {
    LED_OFF,
    LED_ON,          /* recording */
    LED_HEARTBEAT,   /* advertising, waiting for the phone: 40 ms flash every 2 s */
    LED_FAST,        /* connected / transferring: 5 Hz */
} led_pattern_t;

void led_init(void);
void led_set(led_pattern_t pattern);

/* Blocking: n short flashes, then back to the current pattern. 3 = battery low, 5 = storage full. */
void led_flash(int n);

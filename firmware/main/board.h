/* Pin map and product constants for the smart bookmark board, Rev A.
 * Mirrors docs/design_spec.md section 3. Change a pin here and nowhere else. */
#pragma once

#include "driver/gpio.h"

/* ---- pins ---------------------------------------------------------------- */
#define PIN_BUTTON        GPIO_NUM_1    /* SW1 to GND, internal pull-up, RTC wake on low */
#define PIN_LED           GPIO_NUM_2    /* D1, active high */
#define PIN_BAT_ADC       GPIO_NUM_5    /* ADC1_CH4: +BATT / 2 while PIN_BAT_SENSE_EN is high */
#define BAT_ADC_CHANNEL   ADC_CHANNEL_4
#define PIN_BAT_SENSE_EN  GPIO_NUM_16   /* high = battery divider connected */
#define PIN_CHG_STAT_N    GPIO_NUM_17   /* open drain from the charger: low = charging */
#define PIN_VBUS_DET      GPIO_NUM_18   /* VBUS / 2: high = USB present, RTC wake on high */
#define PIN_MIC_DATA      GPIO_NUM_40
#define PIN_MIC_PWR       GPIO_NUM_41   /* powers the microphone; low = off */
#define PIN_MIC_CLK       GPIO_NUM_42

/* External 16 MB clip flash U6 on SPI2 */
#define PIN_FLASH_MISO    GPIO_NUM_10
#define PIN_FLASH_CS      GPIO_NUM_11
#define PIN_FLASH_SCK     GPIO_NUM_12
#define PIN_FLASH_MOSI    GPIO_NUM_13

/* ---- audio ---------------------------------------------------------------- */
#define AUDIO_SAMPLE_RATE     16000
#define AUDIO_GAIN_SHIFT      2         /* PCM is multiplied by 2^n before encoding, with saturation */
#define AUDIO_MIC_SETTLE_MS   120       /* discarded after mic power-up (T3902 wake-up + filter settle) */
#define AUDIO_MIC_SLOT_RIGHT  1         /* T3902 SELECT pin is tied to GND = "right" PDM slot */
#define CLIP_MAX_SECONDS      120
#define CLIP_MIN_MS           400       /* shorter presses are treated as "wake up and sync" */

/* ---- battery -------------------------------------------------------------- */
#define BAT_DIVIDER           2         /* R11 = R12 */
#define BAT_EMPTY_MV          3300      /* refuse to record below this */
#define BAT_FULL_MV           4150

/* ---- behaviour ------------------------------------------------------------ */
#define ADV_AFTER_CLIP_S      30        /* advertise this long after a recording or a button tap */
#define ADV_ON_USB_S          60
#define IDLE_CONNECTED_S      20        /* drop to sleep after this long connected with no traffic */
#define BLE_REQUIRE_ENCRYPTION 1        /* 1 = clip data needs a bonded, encrypted link */
#define DEVICE_NAME           "Bookmark"
#define FW_VERSION_MAJOR      0
#define FW_VERSION_MINOR      1

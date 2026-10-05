/* PDM microphone capture to an ADPCM clip file. */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#include "esp_err.h"

typedef enum {
    AUDIO_STOP_RELEASED,     /* keep_going() returned false */
    AUDIO_STOP_MAX_LENGTH,   /* CLIP_MAX_SECONDS reached */
    AUDIO_STOP_STORAGE,      /* write failed: flash full */
    AUDIO_STOP_ERROR,        /* microphone or file could not be opened */
} audio_stop_t;

/* Power the microphone, record until keep_going() returns false, power it down again.
 * on_started() is called once the first real samples are being stored (LED on).
 * Clips shorter than CLIP_MIN_MS are discarded: *clip_id is then 0. */
audio_stop_t audio_record(bool (*keep_going)(void), void (*on_started)(void),
                          uint32_t *clip_id, uint32_t *duration_ms);

/* Audio clips as LittleFS files named XXXXXXXX.bmk (hex clip id), on the external 16 MB flash
 * first and on the module's "clips" partition once that is full (or if the chip is absent).
 * File = 16-byte header + IMA ADPCM blocks. Ids only ever increase, so the phone can use them
 * to recognise clips it already has. */
#pragma once

#include <stdint.h>
#include <stdio.h>

#include "esp_err.h"

#define CLIP_HEADER_BYTES 16
#define CLIP_CODEC_IMA_ADPCM 1

typedef struct __attribute__((packed)) {
    char     magic[4];        /* "BMK1" */
    uint8_t  version;         /* 1 */
    uint8_t  codec;           /* CLIP_CODEC_IMA_ADPCM */
    uint16_t sample_rate;     /* Hz */
    uint32_t timestamp;       /* Unix seconds at the start of the clip, 0 = clock was not set */
    uint32_t samples;         /* PCM samples encoded (before block padding) */
} clip_header_t;

typedef struct {
    uint32_t id;
    uint32_t size;            /* file size in bytes, header included */
    uint32_t timestamp;
    uint32_t duration_ms;
} clip_info_t;

esp_err_t clip_store_init(void);

/* Unmount the external flash and put it in deep power-down. Call right before deep sleep. */
void clip_store_shutdown(void);

/* Start a new clip. Returns an open file positioned after a placeholder header, or NULL. */
FILE *clip_create(uint32_t *id);

/* Write the real header and close. A clip with samples == 0 is removed. */
esp_err_t clip_finish(FILE *f, uint32_t id, uint32_t samples, uint32_t timestamp);

/* Fill out[] with up to max clips in ascending id order. Returns the number found. */
int clip_list(clip_info_t *out, int max);

FILE *clip_open(uint32_t id, uint32_t *size);
esp_err_t clip_delete(uint32_t id);
void clip_space(uint32_t *total_bytes, uint32_t *used_bytes);

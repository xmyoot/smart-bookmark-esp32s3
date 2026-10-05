/* IMA ADPCM encoder producing WAV-compatible mono blocks (format tag 0x0011).
 * Each 256-byte block: int16 first sample, uint8 step index, 0, then 252 bytes of 4-bit codes
 * (low nibble first) = 505 samples per block. */
#pragma once

#include <stddef.h>
#include <stdint.h>

#define ADPCM_BLOCK_BYTES    256
#define ADPCM_BLOCK_SAMPLES  505

typedef struct {
    int16_t predictor;
    int8_t  index;
    uint16_t fill;                       /* samples already in the current block */
    uint8_t block[ADPCM_BLOCK_BYTES];
} adpcm_enc_t;

void adpcm_init(adpcm_enc_t *e);

/* Feed one sample. Returns 1 when e->block holds a finished block that must be written now. */
int adpcm_put(adpcm_enc_t *e, int16_t sample);

/* Pad the open block with silence. Returns 1 if e->block must be written, 0 if it was empty. */
int adpcm_flush(adpcm_enc_t *e);

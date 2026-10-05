#include "adpcm.h"

#include <string.h>

static const int8_t index_adjust[8] = { -1, -1, -1, -1, 2, 4, 6, 8 };
static const int16_t step_table[89] = {
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
    73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408,
    449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
    2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630,
    9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
};

void adpcm_init(adpcm_enc_t *e)
{
    memset(e, 0, sizeof(*e));
}

static uint8_t encode(adpcm_enc_t *e, int16_t sample)
{
    int step = step_table[e->index];
    int diff = sample - e->predictor;
    uint8_t code = 0;
    if (diff < 0) {
        code = 8;
        diff = -diff;
    }
    int delta = step >> 3;
    if (diff >= step)        { code |= 4; diff -= step;      delta += step; }
    if (diff >= (step >> 1)) { code |= 2; diff -= step >> 1; delta += step >> 1; }
    if (diff >= (step >> 2)) { code |= 1;                    delta += step >> 2; }

    int pred = e->predictor + ((code & 8) ? -delta : delta);
    if (pred > 32767) pred = 32767;
    if (pred < -32768) pred = -32768;
    e->predictor = (int16_t)pred;

    int idx = e->index + index_adjust[code & 7];
    if (idx < 0) idx = 0;
    if (idx > 88) idx = 88;
    e->index = (int8_t)idx;
    return code;
}

int adpcm_put(adpcm_enc_t *e, int16_t sample)
{
    if (e->fill == 0) {                  /* block header carries the first sample verbatim */
        e->predictor = sample;
        e->block[0] = (uint8_t)(sample & 0xff);
        e->block[1] = (uint8_t)((uint16_t)sample >> 8);
        e->block[2] = (uint8_t)e->index;
        e->block[3] = 0;
        memset(e->block + 4, 0, ADPCM_BLOCK_BYTES - 4);
        e->fill = 1;
        return 0;
    }
    uint8_t code = encode(e, sample);
    unsigned n = e->fill - 1;            /* nibble number within the block */
    e->block[4 + n / 2] |= (n & 1) ? (uint8_t)(code << 4) : code;
    if (++e->fill == ADPCM_BLOCK_SAMPLES) {
        e->fill = 0;
        return 1;
    }
    return 0;
}

int adpcm_flush(adpcm_enc_t *e)
{
    if (e->fill == 0) {
        return 0;
    }
    while (!adpcm_put(e, e->predictor)) {
    }
    return 1;
}

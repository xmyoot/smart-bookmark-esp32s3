#include "audio.h"

#include <sys/time.h>

#include "adpcm.h"
#include "board.h"
#include "clip_store.h"
#include "driver/gpio.h"
#include "driver/i2s_pdm.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define CHUNK_SAMPLES 256                /* 16 ms at 16 kHz */
#define TIME_VALID_AFTER 1700000000      /* a clock earlier than this was never set by the phone */

static const char *TAG = "audio";

static i2s_chan_handle_t mic_open(void)
{
    gpio_set_direction(PIN_MIC_PWR, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_MIC_PWR, 1);

    i2s_chan_handle_t rx = NULL;
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    if (i2s_new_channel(&chan_cfg, NULL, &rx) != ESP_OK) {
        return NULL;
    }
    i2s_pdm_rx_config_t cfg = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(AUDIO_SAMPLE_RATE),
        .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = { .clk = PIN_MIC_CLK, .din = PIN_MIC_DATA },
    };
#if AUDIO_MIC_SLOT_RIGHT
    cfg.slot_cfg.slot_mask = I2S_PDM_SLOT_RIGHT;
#endif
    if (i2s_channel_init_pdm_rx_mode(rx, &cfg) != ESP_OK || i2s_channel_enable(rx) != ESP_OK) {
        i2s_del_channel(rx);
        return NULL;
    }
    return rx;
}

static void mic_close(i2s_chan_handle_t rx)
{
    if (rx) {
        i2s_channel_disable(rx);
        i2s_del_channel(rx);
    }
    /* Clock low before removing power, so the clock pin cannot feed the mic through its input. */
    gpio_set_direction(PIN_MIC_CLK, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_MIC_CLK, 0);
    gpio_set_level(PIN_MIC_PWR, 0);
}

audio_stop_t audio_record(bool (*keep_going)(void), void (*on_started)(void),
                          uint32_t *clip_id, uint32_t *duration_ms)
{
    static int16_t pcm[CHUNK_SAMPLES];
    static adpcm_enc_t enc;
    audio_stop_t why = AUDIO_STOP_RELEASED;
    *clip_id = 0;
    *duration_ms = 0;

    i2s_chan_handle_t rx = mic_open();
    if (!rx) {
        ESP_LOGE(TAG, "microphone init failed");
        mic_close(NULL);
        return AUDIO_STOP_ERROR;
    }
    uint32_t id;
    FILE *f = clip_create(&id);
    if (!f) {
        mic_close(rx);
        return AUDIO_STOP_STORAGE;
    }
    struct timeval now;
    gettimeofday(&now, NULL);
    uint32_t stamp = now.tv_sec > TIME_VALID_AFTER ? (uint32_t)now.tv_sec : 0;

    adpcm_init(&enc);
    uint32_t samples = 0;
    int32_t settle = AUDIO_SAMPLE_RATE * AUDIO_MIC_SETTLE_MS / 1000;
    int32_t hp_prev_in = 0, hp_prev_out = 0;     /* one-pole DC blocker, corner about 10 Hz */
    bool started = false;

    while (keep_going()) {
        size_t got = 0;
        if (i2s_channel_read(rx, pcm, sizeof(pcm), &got, pdMS_TO_TICKS(200)) != ESP_OK) {
            why = AUDIO_STOP_ERROR;
            break;
        }
        bool full = false;
        for (size_t i = 0; i < got / sizeof(pcm[0]) && !full; i++) {
            int32_t in = pcm[i];
            int32_t out = in - hp_prev_in + hp_prev_out - (hp_prev_out >> 8);
            hp_prev_in = in;
            hp_prev_out = out;
            if (settle > 0) {
                settle--;
                continue;
            }
            if (!started) {
                started = true;
                if (on_started) {
                    on_started();
                }
            }
            int32_t s = out * (1 << AUDIO_GAIN_SHIFT);
            if (s > 32767) s = 32767;
            if (s < -32768) s = -32768;
            samples++;
            if (adpcm_put(&enc, (int16_t)s) &&
                fwrite(enc.block, 1, ADPCM_BLOCK_BYTES, f) != ADPCM_BLOCK_BYTES) {
                full = true;
            }
        }
        if (full) {
            why = AUDIO_STOP_STORAGE;
            break;
        }
        if (samples >= (uint32_t)CLIP_MAX_SECONDS * AUDIO_SAMPLE_RATE) {
            why = AUDIO_STOP_MAX_LENGTH;
            break;
        }
    }
    mic_close(rx);

    if (adpcm_flush(&enc)) {
        fwrite(enc.block, 1, ADPCM_BLOCK_BYTES, f);
    }
    uint32_t ms = (uint32_t)((uint64_t)samples * 1000 / AUDIO_SAMPLE_RATE);
    bool keep = ms >= CLIP_MIN_MS;
    if (clip_finish(f, id, keep ? samples : 0, stamp) != ESP_OK) {
        why = AUDIO_STOP_STORAGE;
        keep = false;
    }
    if (keep) {
        *clip_id = id;
        *duration_ms = ms;
        ESP_LOGI(TAG, "clip %lu: %lu ms", (unsigned long)id, (unsigned long)ms);
    }
    return why;
}

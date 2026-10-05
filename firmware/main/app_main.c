/* Smart bookmark voice recorder.
 *
 * The device spends its life in deep sleep. It wakes on the button or when USB is plugged in:
 *   button held    -> record while held (LED on), store the clip
 *   then           -> advertise so the phone can fetch clips (LED heartbeat), serve it (LED fast)
 *   nothing to do  -> back to deep sleep
 * A second press while awake records another clip; BLE stays up meanwhile.
 */
#include "audio.h"
#include "ble_xfer.h"
#include "board.h"
#include "clip_store.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "led.h"
#include "nvs_flash.h"
#include "power.h"

static const char *TAG = "app";

static void recording_started(void)
{
    led_set(LED_ON);
}

/* Record one clip while the button is held. Returns true if a clip was stored. */
static bool record_clip(void)
{
    int mv = power_battery_mv();
    if (mv < BAT_EMPTY_MV && !power_usb_present()) {
        ESP_LOGW(TAG, "battery %d mV: not recording", mv);
        led_flash(3);
        return false;
    }
    uint32_t id, ms;
    audio_stop_t why = audio_record(power_button_down, recording_started, &id, &ms);
    led_set(LED_OFF);
    if (why == AUDIO_STOP_STORAGE) {
        led_flash(5);                    /* flash full: sync with the phone to free space */
    } else if (why == AUDIO_STOP_ERROR) {
        led_flash(8);
    }
    return id != 0;
}

static void report_battery(void)
{
    int mv = power_battery_mv();
    ble_xfer_set_battery(power_battery_percent(mv), (uint16_t)mv);
}

void app_main(void)
{
    esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
    power_init();
    led_init();

    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
    bool storage_ok = clip_store_init() == ESP_OK;

    /* Recording comes first: the radio is not started until the user has finished speaking. */
    if (storage_ok && power_button_down()) {
        record_clip();
    }

    int adv_seconds = cause == ESP_SLEEP_WAKEUP_EXT1 ? ADV_ON_USB_S : ADV_AFTER_CLIP_S;
    ble_xfer_start();
    report_battery();
    ble_xfer_advertise(adv_seconds);
    int64_t awake_until = esp_timer_get_time() + (int64_t)adv_seconds * 1000000;

    for (;;) {
        if (storage_ok && power_button_down()) {
            vTaskDelay(pdMS_TO_TICKS(20));               /* debounce */
            if (power_button_down()) {
                record_clip();
                report_battery();
                ble_xfer_advertise(ADV_AFTER_CLIP_S);
                awake_until = esp_timer_get_time() + (int64_t)ADV_AFTER_CLIP_S * 1000000;
            }
        }
        if (ble_xfer_connected()) {
            led_set(LED_FAST);
            if (ble_xfer_idle_ms() > IDLE_CONNECTED_S * 1000) {
                break;                                   /* phone is connected but silent */
            }
        } else {
            led_set(LED_HEARTBEAT);
            if (esp_timer_get_time() > awake_until) {
                break;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(20));
    }
    led_set(LED_OFF);
    clip_store_shutdown();
    power_deep_sleep();
}

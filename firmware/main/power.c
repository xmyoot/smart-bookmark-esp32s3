#include "power.h"

#include "board.h"
#include "driver/gpio.h"
#include "driver/rtc_io.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_log.h"
#include "esp_sleep.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "power";
static adc_oneshot_unit_handle_t s_adc;
static adc_cali_handle_t s_cali;

void power_init(void)
{
    /* Pins were RTC-held for the wake sources; hand them back to the digital domain. */
    rtc_gpio_deinit(PIN_BUTTON);
    rtc_gpio_deinit(PIN_VBUS_DET);

    gpio_config_t in_pullup = {
        .pin_bit_mask = (1ULL << PIN_BUTTON) | (1ULL << PIN_CHG_STAT_N),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
    };
    gpio_config(&in_pullup);
    gpio_config_t in_plain = {
        .pin_bit_mask = 1ULL << PIN_VBUS_DET,
        .mode = GPIO_MODE_INPUT,
    };
    gpio_config(&in_plain);
    gpio_config_t out = {
        .pin_bit_mask = (1ULL << PIN_BAT_SENSE_EN) | (1ULL << PIN_MIC_PWR),
        .mode = GPIO_MODE_OUTPUT,
    };
    gpio_config(&out);
    gpio_set_level(PIN_BAT_SENSE_EN, 0);
    gpio_set_level(PIN_MIC_PWR, 0);

    adc_oneshot_unit_init_cfg_t unit = { .unit_id = ADC_UNIT_1 };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit, &s_adc));
    adc_oneshot_chan_cfg_t chan = { .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(s_adc, BAT_ADC_CHANNEL, &chan));
    adc_cali_curve_fitting_config_t cali = {
        .unit_id = ADC_UNIT_1,
        .chan = BAT_ADC_CHANNEL,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    if (adc_cali_create_scheme_curve_fitting(&cali, &s_cali) != ESP_OK) {
        ESP_LOGW(TAG, "no ADC calibration; battery reading will be approximate");
        s_cali = NULL;
    }
}

bool power_button_down(void)
{
    return gpio_get_level(PIN_BUTTON) == 0;
}

bool power_usb_present(void)
{
    return gpio_get_level(PIN_VBUS_DET) == 1;
}

bool power_charging(void)
{
    return power_usb_present() && gpio_get_level(PIN_CHG_STAT_N) == 0;
}

int power_battery_mv(void)
{
    gpio_set_level(PIN_BAT_SENSE_EN, 1);
    vTaskDelay(pdMS_TO_TICKS(30));              /* C6 charges through R11 || R12: 5 ms time constant */
    int sum = 0, n = 0;
    for (int i = 0; i < 8; i++) {
        int raw, mv;
        if (adc_oneshot_read(s_adc, BAT_ADC_CHANNEL, &raw) != ESP_OK) {
            continue;
        }
        if (s_cali && adc_cali_raw_to_voltage(s_cali, raw, &mv) == ESP_OK) {
            sum += mv;
        } else {
            sum += raw * 3100 / 4095;
        }
        n++;
    }
    gpio_set_level(PIN_BAT_SENSE_EN, 0);
    return n ? sum / n * BAT_DIVIDER : 0;
}

uint8_t power_battery_percent(int mv)
{
    /* Resting LiPo curve, coarse. Reads high while charging and low under radio load. */
    static const struct { int mv; int pct; } curve[] = {
        { 4150, 100 }, { 4000, 85 }, { 3900, 70 }, { 3800, 55 }, { 3700, 35 },
        { 3600, 20 }, { 3500, 10 }, { 3300, 0 },
    };
    if (mv >= curve[0].mv) {
        return 100;
    }
    for (int i = 1; i < (int)(sizeof(curve) / sizeof(curve[0])); i++) {
        if (mv >= curve[i].mv) {
            int span = curve[i - 1].mv - curve[i].mv;
            return (uint8_t)(curve[i].pct + (mv - curve[i].mv) * (curve[i - 1].pct - curve[i].pct) / span);
        }
    }
    return 0;
}

void power_deep_sleep(void)
{
    gpio_set_level(PIN_LED, 0);
    gpio_set_level(PIN_MIC_PWR, 0);
    gpio_set_level(PIN_BAT_SENSE_EN, 0);

    /* A held button would wake the chip again at once: wait for release first. */
    while (power_button_down()) {
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    vTaskDelay(pdMS_TO_TICKS(30));

    rtc_gpio_init(PIN_BUTTON);
    rtc_gpio_set_direction(PIN_BUTTON, RTC_GPIO_MODE_INPUT_ONLY);
    rtc_gpio_pulldown_dis(PIN_BUTTON);
    rtc_gpio_pullup_en(PIN_BUTTON);
    esp_sleep_enable_ext0_wakeup(PIN_BUTTON, 0);
    if (!power_usb_present()) {
        esp_sleep_enable_ext1_wakeup(1ULL << PIN_VBUS_DET, ESP_EXT1_WAKEUP_ANY_HIGH);
    }
    ESP_LOGI(TAG, "deep sleep");
    esp_deep_sleep_start();
}

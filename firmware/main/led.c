#include "led.h"

#include <stdbool.h>

#include "board.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define TICK_MS 40

static volatile led_pattern_t s_pattern = LED_OFF;
static volatile bool s_paused;
static unsigned s_tick;

static void on_tick(void *arg)
{
    if (s_paused) {
        return;
    }
    s_tick++;
    int level = 0;
    switch (s_pattern) {
    case LED_ON:        level = 1; break;
    case LED_HEARTBEAT: level = (s_tick % (2000 / TICK_MS)) == 0; break;
    case LED_FAST:      level = (s_tick % 5) < 2; break;
    default:            break;
    }
    gpio_set_level(PIN_LED, level);
}

void led_init(void)
{
    gpio_set_direction(PIN_LED, GPIO_MODE_OUTPUT);
    gpio_set_level(PIN_LED, 0);
    const esp_timer_create_args_t args = { .callback = on_tick, .name = "led" };
    esp_timer_handle_t timer;
    ESP_ERROR_CHECK(esp_timer_create(&args, &timer));
    ESP_ERROR_CHECK(esp_timer_start_periodic(timer, TICK_MS * 1000));
}

void led_set(led_pattern_t pattern)
{
    s_pattern = pattern;
    if (pattern == LED_ON || pattern == LED_OFF) {
        gpio_set_level(PIN_LED, pattern == LED_ON);   /* no wait for the next tick */
    }
}

void led_flash(int n)
{
    s_paused = true;
    for (int i = 0; i < n; i++) {
        gpio_set_level(PIN_LED, 1);
        vTaskDelay(pdMS_TO_TICKS(80));
        gpio_set_level(PIN_LED, 0);
        vTaskDelay(pdMS_TO_TICKS(120));
    }
    s_paused = false;
}

idf_component_register(
    SRCS "app_main.c" "adpcm.c" "audio.c" "ble_xfer.c" "clip_store.c" "led.c" "power.c"
    INCLUDE_DIRS "."
    PRIV_REQUIRES bt esp_adc esp_driver_gpio esp_driver_i2s esp_timer nvs_flash)

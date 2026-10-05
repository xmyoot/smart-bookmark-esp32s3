#include "ext_flash.h"

#include "board.h"
#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_flash.h"
#include "esp_flash_spi_init.h"
#include "esp_log.h"
#include "esp_rom_sys.h"

#define CMD_POWER_DOWN          0xB9
#define CMD_RELEASE_POWER_DOWN  0xAB
#define HOST                    SPI2_HOST

static const char *TAG = "extflash";
static esp_flash_t *s_chip;
static bool s_bus_up;

/* The two power commands are clocked out by hand (SPI mode 0, MSB first). They are needed
 * before the flash driver exists and after it is gone, so the driver cannot send them. */
static void bitbang_command(uint8_t cmd)
{
    const gpio_num_t pins[] = { PIN_FLASH_CS, PIN_FLASH_SCK, PIN_FLASH_MOSI };
    for (int i = 0; i < 3; i++) {
        gpio_reset_pin(pins[i]);
        gpio_set_direction(pins[i], GPIO_MODE_OUTPUT);
    }
    gpio_set_level(PIN_FLASH_CS, 1);
    gpio_set_level(PIN_FLASH_SCK, 0);
    esp_rom_delay_us(2);
    gpio_set_level(PIN_FLASH_CS, 0);
    for (int bit = 7; bit >= 0; bit--) {
        gpio_set_level(PIN_FLASH_MOSI, (cmd >> bit) & 1);
        esp_rom_delay_us(1);
        gpio_set_level(PIN_FLASH_SCK, 1);
        esp_rom_delay_us(1);
        gpio_set_level(PIN_FLASH_SCK, 0);
    }
    gpio_set_level(PIN_FLASH_CS, 1);
    esp_rom_delay_us(50);                /* tRES1 / tDP: the chip needs a moment after either command */
}

const esp_partition_t *ext_flash_start(void)
{
    bitbang_command(CMD_RELEASE_POWER_DOWN);

    const spi_bus_config_t bus = {
        .mosi_io_num = PIN_FLASH_MOSI,
        .miso_io_num = PIN_FLASH_MISO,
        .sclk_io_num = PIN_FLASH_SCK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
    };
    if (spi_bus_initialize(HOST, &bus, SPI_DMA_CH_AUTO) != ESP_OK) {
        return NULL;
    }
    s_bus_up = true;
    const esp_flash_spi_device_config_t dev = {
        .host_id = HOST,
        .cs_io_num = PIN_FLASH_CS,
        .io_mode = SPI_FLASH_FASTRD,
        .freq_mhz = 20,
    };
    uint32_t size = 0;
    if (spi_bus_add_flash_device(&s_chip, &dev) != ESP_OK ||
        esp_flash_init(s_chip) != ESP_OK ||
        esp_flash_get_size(s_chip, &size) != ESP_OK || size == 0) {
        ESP_LOGW(TAG, "no external flash; using the module flash only");
        ext_flash_sleep();
        return NULL;
    }
    const esp_partition_t *part = NULL;
    if (esp_partition_register_external(s_chip, 0, size, "clips_ext", ESP_PARTITION_TYPE_DATA,
                                        ESP_PARTITION_SUBTYPE_DATA_SPIFFS, &part) != ESP_OK) {
        ext_flash_sleep();
        return NULL;
    }
    ESP_LOGI(TAG, "external flash: %lu MB", (unsigned long)(size >> 20));
    return part;
}

void ext_flash_sleep(void)
{
    if (s_chip) {
        spi_bus_remove_flash_device(s_chip);
        s_chip = NULL;
    }
    if (s_bus_up) {
        spi_bus_free(HOST);
        s_bus_up = false;
    }
    bitbang_command(CMD_POWER_DOWN);
    /* CS floats in deep sleep; R16 holds it high so the chip stays deselected. */
}

/* External 16 MB SPI NOR flash (U6, W25Q128JV) on SPI2, exposed as one data partition. */
#pragma once

#include "esp_partition.h"

/* Wake the chip from deep power-down, probe it and register it as a partition.
 * Returns NULL if the chip does not answer (not fitted, or faulty): callers fall back
 * to the module's own flash. */
const esp_partition_t *ext_flash_start(void);

/* Release the SPI bus and put the chip in deep power-down (about 1 uA instead of standby
 * current). Call after every filesystem on it is unmounted, right before deep sleep. */
void ext_flash_sleep(void);

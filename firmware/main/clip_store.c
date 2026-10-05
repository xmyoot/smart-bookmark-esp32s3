#include "clip_store.h"

#include <dirent.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "board.h"
#include "esp_littlefs.h"
#include "esp_log.h"
#include "nvs.h"

#define MOUNT      "/fs"
#define PARTITION  "clips"
#define NVS_SPACE  "clips"
#define NVS_NEXT   "next_id"

static const char *TAG = "clips";

static void clip_path(char *buf, size_t len, uint32_t id)
{
    snprintf(buf, len, MOUNT "/%08lx.bmk", (unsigned long)id);
}

esp_err_t clip_store_init(void)
{
    esp_vfs_littlefs_conf_t conf = {
        .base_path = MOUNT,
        .partition_label = PARTITION,
        .format_if_mount_failed = true,
    };
    esp_err_t err = esp_vfs_littlefs_register(&conf);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "mount failed: %s", esp_err_to_name(err));
    }
    return err;
}

static uint32_t take_next_id(void)
{
    nvs_handle_t h;
    uint32_t id = 1;
    if (nvs_open(NVS_SPACE, NVS_READWRITE, &h) != ESP_OK) {
        return 0;
    }
    nvs_get_u32(h, NVS_NEXT, &id);
    nvs_set_u32(h, NVS_NEXT, id + 1);
    nvs_commit(h);
    nvs_close(h);
    return id;
}

FILE *clip_create(uint32_t *id)
{
    char path[32];
    *id = take_next_id();
    if (*id == 0) {
        return NULL;
    }
    clip_path(path, sizeof(path), *id);
    FILE *f = fopen(path, "w+b");
    if (!f) {
        ESP_LOGE(TAG, "cannot create %s", path);
        return NULL;
    }
    setvbuf(f, NULL, _IOFBF, 4096);
    clip_header_t hdr = { 0 };
    if (fwrite(&hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        fclose(f);
        unlink(path);
        return NULL;
    }
    return f;
}

esp_err_t clip_finish(FILE *f, uint32_t id, uint32_t samples, uint32_t timestamp)
{
    char path[32];
    clip_path(path, sizeof(path), id);
    clip_header_t hdr = {
        .magic = { 'B', 'M', 'K', '1' },
        .version = 1,
        .codec = CLIP_CODEC_IMA_ADPCM,
        .sample_rate = AUDIO_SAMPLE_RATE,
        .timestamp = timestamp,
        .samples = samples,
    };
    bool ok = fseek(f, 0, SEEK_SET) == 0 && fwrite(&hdr, 1, sizeof(hdr), f) == sizeof(hdr);
    ok = (fclose(f) == 0) && ok;
    if (!ok || samples == 0) {
        unlink(path);
        return ok ? ESP_OK : ESP_FAIL;
    }
    return ESP_OK;
}

static int by_id(const void *a, const void *b)
{
    uint32_t x = ((const clip_info_t *)a)->id, y = ((const clip_info_t *)b)->id;
    return (x > y) - (x < y);
}

int clip_list(clip_info_t *out, int max)
{
    DIR *d = opendir(MOUNT);
    if (!d) {
        return 0;
    }
    int n = 0;
    struct dirent *e;
    while (n < max && (e = readdir(d)) != NULL) {
        char *end;
        uint32_t id = strtoul(e->d_name, &end, 16);
        if (end != e->d_name + 8 || strcmp(end, ".bmk") != 0) {
            continue;
        }
        char path[32];
        clip_path(path, sizeof(path), id);
        clip_header_t hdr;
        struct stat st;
        FILE *f = fopen(path, "rb");
        if (!f) {
            continue;
        }
        bool ok = fread(&hdr, 1, sizeof(hdr), f) == sizeof(hdr) && memcmp(hdr.magic, "BMK1", 4) == 0;
        fclose(f);
        if (!ok || stat(path, &st) != 0) {
            unlink(path);                /* interrupted recording (power loss): header never written */
            continue;
        }
        out[n].id = id;
        out[n].size = (uint32_t)st.st_size;
        out[n].timestamp = hdr.timestamp;
        out[n].duration_ms = (uint32_t)((uint64_t)hdr.samples * 1000 / (hdr.sample_rate ? hdr.sample_rate : 1));
        n++;
    }
    closedir(d);
    qsort(out, n, sizeof(out[0]), by_id);
    return n;
}

FILE *clip_open(uint32_t id, uint32_t *size)
{
    char path[32];
    struct stat st;
    clip_path(path, sizeof(path), id);
    if (stat(path, &st) != 0) {
        return NULL;
    }
    *size = (uint32_t)st.st_size;
    return fopen(path, "rb");
}

esp_err_t clip_delete(uint32_t id)
{
    char path[32];
    clip_path(path, sizeof(path), id);
    return unlink(path) == 0 ? ESP_OK : ESP_ERR_NOT_FOUND;
}

void clip_space(uint32_t *total_bytes, uint32_t *used_bytes)
{
    size_t total = 0, used = 0;
    esp_littlefs_info(PARTITION, &total, &used);
    *total_bytes = (uint32_t)total;
    *used_bytes = (uint32_t)used;
}

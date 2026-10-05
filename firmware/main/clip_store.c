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
#include "ext_flash.h"
#include "nvs.h"

#define NVS_SPACE  "clips"
#define NVS_NEXT   "next_id"
#define MIN_FREE   (64 * 1024)      /* a store with less than this is treated as full for new clips */

/* Two stores, filled in this order: the 16 MB external flash U6, then the "clips" partition on
 * the module's own flash. A clip lives wholly in one of them; ids are unique across both. */
typedef struct {
    const char *mount;
    const char *label;               /* internal partition label, or NULL for the external chip */
    const esp_partition_t *part;     /* external partition once registered */
    bool ok;
} store_t;

static store_t s_stores[] = {
    { .mount = "/x" },
    { .mount = "/fs", .label = "clips" },
};
#define N_STORES ((int)(sizeof(s_stores) / sizeof(s_stores[0])))

static const char *TAG = "clips";

static void clip_path(char *buf, size_t len, const store_t *s, uint32_t id)
{
    snprintf(buf, len, "%s/%08lx.bmk", s->mount, (unsigned long)id);
}

static void store_info(const store_t *s, size_t *total, size_t *used)
{
    *total = *used = 0;
    if (!s->ok) {
        return;
    }
    if (s->part) {
        esp_littlefs_partition_info(s->part, total, used);
    } else {
        esp_littlefs_info(s->label, total, used);
    }
}

/* Path of an existing clip, searching both stores. */
static bool find_clip(uint32_t id, char *path, size_t len, struct stat *st)
{
    for (int i = 0; i < N_STORES; i++) {
        if (!s_stores[i].ok) {
            continue;
        }
        clip_path(path, len, &s_stores[i], id);
        if (stat(path, st) == 0) {
            return true;
        }
    }
    return false;
}

esp_err_t clip_store_init(void)
{
    s_stores[0].part = ext_flash_start();
    for (int i = 0; i < N_STORES; i++) {
        store_t *s = &s_stores[i];
        if (!s->label && !s->part) {
            continue;                                   /* external chip absent */
        }
        esp_vfs_littlefs_conf_t conf = {
            .base_path = s->mount,
            .partition_label = s->label,
            .partition = s->part,
            .format_if_mount_failed = true,
        };
        esp_err_t err = esp_vfs_littlefs_register(&conf);
        s->ok = err == ESP_OK;
        if (!s->ok) {
            ESP_LOGE(TAG, "mount %s failed: %s", s->mount, esp_err_to_name(err));
        }
    }
    return (s_stores[0].ok || s_stores[1].ok) ? ESP_OK : ESP_FAIL;
}

void clip_store_shutdown(void)
{
    if (s_stores[0].ok) {
        esp_vfs_littlefs_unregister_partition(s_stores[0].part);
        s_stores[0].ok = false;
    }
    ext_flash_sleep();
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
    const store_t *target = NULL;
    for (int i = 0; i < N_STORES && !target; i++) {
        size_t total, used;
        store_info(&s_stores[i], &total, &used);
        if (total - used >= MIN_FREE) {
            target = &s_stores[i];
        }
    }
    *id = target ? take_next_id() : 0;
    if (*id == 0) {
        return NULL;
    }
    char path[32];
    clip_path(path, sizeof(path), target, *id);
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
        clip_delete(id);
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
    int n = 0;
    for (int i = 0; i < N_STORES; i++) {
        const store_t *s = &s_stores[i];
        DIR *d = s->ok ? opendir(s->mount) : NULL;
        if (!d) {
            continue;
        }
        struct dirent *e;
        while (n < max && (e = readdir(d)) != NULL) {
            char *end;
            uint32_t id = strtoul(e->d_name, &end, 16);
            if (end != e->d_name + 8 || strcmp(end, ".bmk") != 0) {
                continue;
            }
            char path[32];
            clip_path(path, sizeof(path), s, id);
            clip_header_t hdr;
            struct stat st;
            FILE *f = fopen(path, "rb");
            if (!f) {
                continue;
            }
            bool ok = fread(&hdr, 1, sizeof(hdr), f) == sizeof(hdr) && memcmp(hdr.magic, "BMK1", 4) == 0;
            fclose(f);
            if (!ok || stat(path, &st) != 0) {
                unlink(path);            /* interrupted recording (power loss): header never written */
                continue;
            }
            out[n].id = id;
            out[n].size = (uint32_t)st.st_size;
            out[n].timestamp = hdr.timestamp;
            out[n].duration_ms = (uint32_t)((uint64_t)hdr.samples * 1000 / (hdr.sample_rate ? hdr.sample_rate : 1));
            n++;
        }
        closedir(d);
    }
    qsort(out, n, sizeof(out[0]), by_id);
    return n;
}

FILE *clip_open(uint32_t id, uint32_t *size)
{
    char path[32];
    struct stat st;
    if (!find_clip(id, path, sizeof(path), &st)) {
        return NULL;
    }
    *size = (uint32_t)st.st_size;
    return fopen(path, "rb");
}

esp_err_t clip_delete(uint32_t id)
{
    char path[32];
    struct stat st;
    if (!find_clip(id, path, sizeof(path), &st)) {
        return ESP_ERR_NOT_FOUND;
    }
    return unlink(path) == 0 ? ESP_OK : ESP_FAIL;
}

void clip_space(uint32_t *total_bytes, uint32_t *used_bytes)
{
    *total_bytes = *used_bytes = 0;
    for (int i = 0; i < N_STORES; i++) {
        size_t total, used;
        store_info(&s_stores[i], &total, &used);
        *total_bytes += (uint32_t)total;
        *used_bytes += (uint32_t)used;
    }
}

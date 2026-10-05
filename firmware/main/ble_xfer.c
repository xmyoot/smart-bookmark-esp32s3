#include "ble_xfer.h"

#include <string.h>
#include <sys/time.h>

#include "adpcm.h"
#include "board.h"
#include "clip_store.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_rom_crc.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "host/ble_hs.h"
#include "host/util/util.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "power.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"

void ble_store_config_init(void);        /* NimBLE bond storage (NVS); has no public header */

/* ---- protocol (docs/ble_protocol.md) ---------------------------------------- */
#define PROTO_VERSION 1

enum {                                   /* phone -> device, Control characteristic */
    OP_GET_INFO = 0x01, OP_LIST = 0x02, OP_READ = 0x03, OP_ABORT = 0x04, OP_DELETE = 0x05, OP_SET_TIME = 0x06,
};
enum {                                   /* device -> phone, Control characteristic */
    EV_INFO = 0x81, EV_LIST_ENTRY = 0x82, EV_LIST_END = 0x83, EV_READ_DONE = 0x84, EV_DELETED = 0x85,
    EV_TIME_SET = 0x86, EV_ERROR = 0xff,
};
enum {
    ERR_UNKNOWN_OPCODE = 1, ERR_BAD_LENGTH = 2, ERR_NO_SUCH_CLIP = 3, ERR_BAD_OFFSET = 4, ERR_BUSY = 5,
    ERR_ABORTED = 6, ERR_IO = 7,
};

/* b00c0001-6e2f-4c1a-9d3e-7a5b10f0c0de and ...0002 (Control), ...0003 (Data) */
#define UUID_BOOKMARK(n) BLE_UUID128_INIT(0xde, 0xc0, 0xf0, 0x10, 0x5b, 0x7a, 0x3e, 0x9d, \
                                          0x1a, 0x4c, 0x2f, 0x6e, (n), 0x00, 0x0c, 0xb0)
static const ble_uuid128_t uuid_service = UUID_BOOKMARK(0x01);
static const ble_uuid128_t uuid_control = UUID_BOOKMARK(0x02);
static const ble_uuid128_t uuid_data = UUID_BOOKMARK(0x03);

#define MAX_CLIPS 256

typedef struct {
    uint8_t op;
    uint32_t a, b;
} cmd_t;

static const char *TAG = "ble";
static uint16_t s_conn = BLE_HS_CONN_HANDLE_NONE;
static uint16_t s_control_handle, s_data_handle, s_battery_handle;
static uint8_t s_own_addr_type;
static volatile bool s_advertising, s_abort, s_busy;
static volatile int64_t s_last_activity_us;
static uint8_t s_battery_pct = 100;
static uint16_t s_battery_mv;
static QueueHandle_t s_queue;
static int s_adv_seconds;
static clip_info_t s_clips[MAX_CLIPS];        /* used by the transfer task only */

static void touch(void)
{
    s_last_activity_us = esp_timer_get_time();
}

/* ---- sending ---------------------------------------------------------------- */
static int notify(uint16_t handle, const void *buf, size_t len)
{
    for (int tries = 0; tries < 400; tries++) {
        if (s_conn == BLE_HS_CONN_HANDLE_NONE) {
            return BLE_HS_ENOTCONN;
        }
        struct os_mbuf *om = ble_hs_mbuf_from_flat(buf, len);
        int rc = om ? ble_gatts_notify_custom(s_conn, handle, om) : BLE_HS_ENOMEM;
        if (rc == 0) {
            touch();
            return 0;
        }
        if (rc != BLE_HS_ENOMEM && rc != BLE_HS_EBUSY) {
            return rc;
        }
        vTaskDelay(pdMS_TO_TICKS(5));    /* controller queue full: let the radio drain it */
    }
    return BLE_HS_ETIMEOUT;
}

static void put32(uint8_t *p, uint32_t v)
{
    p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24;
}

static uint32_t get32(const uint8_t *p)
{
    return p[0] | (p[1] << 8) | (p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void send_error(uint8_t op, uint8_t code)
{
    uint8_t m[3] = { EV_ERROR, op, code };
    notify(s_control_handle, m, sizeof(m));
}

/* ---- command handlers (transfer task) ---------------------------------------- */
static void do_info(void)
{
    uint32_t total, used;
    clip_space(&total, &used);
    int n = clip_list(s_clips, MAX_CLIPS);
    uint8_t m[22] = { EV_INFO, PROTO_VERSION, FW_VERSION_MAJOR, FW_VERSION_MINOR, CLIP_CODEC_IMA_ADPCM };
    m[5] = AUDIO_SAMPLE_RATE & 0xff;  m[6] = AUDIO_SAMPLE_RATE >> 8;
    m[7] = ADPCM_BLOCK_BYTES & 0xff;  m[8] = ADPCM_BLOCK_BYTES >> 8;
    m[9] = n & 0xff;                  m[10] = n >> 8;
    put32(m + 11, total);
    put32(m + 15, used);
    m[19] = s_battery_mv & 0xff;      m[20] = s_battery_mv >> 8;
    m[21] = (power_usb_present() ? 1 : 0) | (power_charging() ? 2 : 0);
    notify(s_control_handle, m, sizeof(m));
}

static void do_list(void)
{
    int n = clip_list(s_clips, MAX_CLIPS);
    for (int i = 0; i < n && !s_abort; i++) {
        uint8_t m[17] = { EV_LIST_ENTRY };
        put32(m + 1, s_clips[i].id);
        put32(m + 5, s_clips[i].size);
        put32(m + 9, s_clips[i].timestamp);
        put32(m + 13, s_clips[i].duration_ms);
        if (notify(s_control_handle, m, sizeof(m)) != 0) {
            return;
        }
    }
    uint8_t end[3] = { EV_LIST_END, n & 0xff, n >> 8 };
    notify(s_control_handle, end, sizeof(end));
}

static void do_read(uint32_t id, uint32_t offset)
{
    static uint8_t pkt[4 + 512];
    uint32_t size;
    FILE *f = clip_open(id, &size);
    if (!f) {
        send_error(OP_READ, ERR_NO_SUCH_CLIP);
        return;
    }
    if (offset > size) {
        fclose(f);
        send_error(OP_READ, ERR_BAD_OFFSET);
        return;
    }
    /* The CRC always covers the whole file, so a resumed transfer is still verified end to end. */
    uint32_t crc = 0, pos = 0;
    while (pos < offset) {
        size_t n = fread(pkt, 1, offset - pos < sizeof(pkt) ? offset - pos : sizeof(pkt), f);
        if (n == 0) {
            break;
        }
        crc = esp_rom_crc32_le(crc, pkt, n);
        pos += n;
    }
    uint8_t err = pos == offset ? 0 : ERR_IO;
    while (!err && pos < size) {
        if (s_abort) {
            err = ERR_ABORTED;
            break;
        }
        size_t room = ble_att_mtu(s_conn) - 3 - 4;      /* ATT header, then our 4-byte offset */
        if (room > sizeof(pkt) - 4) {
            room = sizeof(pkt) - 4;
        }
        size_t n = fread(pkt + 4, 1, size - pos < room ? size - pos : room, f);
        if (n == 0) {
            err = ERR_IO;
            break;
        }
        put32(pkt, pos);
        if (notify(s_data_handle, pkt, 4 + n) != 0) {
            fclose(f);
            return;                                     /* link lost: nothing more to say */
        }
        crc = esp_rom_crc32_le(crc, pkt + 4, n);
        pos += n;
    }
    fclose(f);
    if (err) {
        send_error(OP_READ, err);
        return;
    }
    uint8_t m[13] = { EV_READ_DONE };
    put32(m + 1, id);
    put32(m + 5, size);
    put32(m + 9, crc);
    notify(s_control_handle, m, sizeof(m));
}

static void transfer_task(void *arg)
{
    cmd_t c;
    for (;;) {
        xQueueReceive(s_queue, &c, portMAX_DELAY);
        s_busy = true;
        s_abort = false;
        switch (c.op) {
        case OP_GET_INFO:
            do_info();
            break;
        case OP_LIST:
            do_list();
            break;
        case OP_READ:
            do_read(c.a, c.b);
            break;
        case OP_DELETE: {
            if (clip_delete(c.a) != ESP_OK) {
                send_error(OP_DELETE, ERR_NO_SUCH_CLIP);
                break;
            }
            uint8_t m[5] = { EV_DELETED };
            put32(m + 1, c.a);
            notify(s_control_handle, m, sizeof(m));
            break;
        }
        case OP_SET_TIME: {
            struct timeval tv = { .tv_sec = c.a };
            settimeofday(&tv, NULL);
            uint8_t m[1] = { EV_TIME_SET };
            notify(s_control_handle, m, sizeof(m));
            break;
        }
        default:
            break;
        }
        s_busy = false;
    }
}

/* ---- GATT --------------------------------------------------------------------- */
static int on_control(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    static const uint8_t arg_len[] = { [OP_GET_INFO] = 0, [OP_LIST] = 0, [OP_READ] = 8, [OP_ABORT] = 0,
                                       [OP_DELETE] = 4, [OP_SET_TIME] = 4 };
    uint8_t buf[9];
    uint16_t len = 0;
    if (ctxt->op != BLE_GATT_ACCESS_OP_WRITE_CHR) {
        return BLE_ATT_ERR_UNLIKELY;
    }
    if (ble_hs_mbuf_to_flat(ctxt->om, buf, sizeof(buf), &len) != 0 || len < 1) {
        return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
    }
    touch();
    uint8_t op = buf[0];
    if (op < OP_GET_INFO || op > OP_SET_TIME) {
        send_error(op, ERR_UNKNOWN_OPCODE);
        return 0;
    }
    if (len != 1 + arg_len[op]) {
        send_error(op, ERR_BAD_LENGTH);
        return 0;
    }
    if (op == OP_ABORT) {
        s_abort = true;                                 /* seen by the running LIST / READ */
        return 0;
    }
    cmd_t c = { .op = op, .a = len >= 5 ? get32(buf + 1) : 0, .b = len >= 9 ? get32(buf + 5) : 0 };
    if (s_busy || xQueueSend(s_queue, &c, 0) != pdTRUE) {
        send_error(op, ERR_BUSY);
    }
    return 0;
}

static int on_data(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    return BLE_ATT_ERR_READ_NOT_PERMITTED;              /* notify-only */
}

static int on_battery(uint16_t conn, uint16_t attr, struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    return os_mbuf_append(ctxt->om, &s_battery_pct, 1) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

#if BLE_REQUIRE_ENCRYPTION
#define SECURE_WRITE BLE_GATT_CHR_F_WRITE_ENC
#else
#define SECURE_WRITE 0
#endif

static const struct ble_gatt_svc_def services[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &uuid_service.u,
        .characteristics = (struct ble_gatt_chr_def[]) {
            { .uuid = &uuid_control.u, .access_cb = on_control, .val_handle = &s_control_handle,
              .flags = BLE_GATT_CHR_F_WRITE | SECURE_WRITE | BLE_GATT_CHR_F_NOTIFY },
            { .uuid = &uuid_data.u, .access_cb = on_data, .val_handle = &s_data_handle,
              .flags = BLE_GATT_CHR_F_NOTIFY },
            { 0 },
        },
    },
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = BLE_UUID16_DECLARE(0x180f),             /* Battery Service */
        .characteristics = (struct ble_gatt_chr_def[]) {
            { .uuid = BLE_UUID16_DECLARE(0x2a19), .access_cb = on_battery, .val_handle = &s_battery_handle,
              .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY },
            { 0 },
        },
    },
    { 0 },
};

/* ---- GAP ---------------------------------------------------------------------- */
static int on_gap(struct ble_gap_event *ev, void *arg);

static void start_advertising(void)
{
    if (s_conn != BLE_HS_CONN_HANDLE_NONE || s_adv_seconds <= 0) {
        return;
    }
    struct ble_hs_adv_fields adv = { 0 }, rsp = { 0 };
    adv.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    adv.uuids128 = (ble_uuid128_t *)&uuid_service;
    adv.num_uuids128 = 1;
    adv.uuids128_is_complete = 1;
    const char *name = ble_svc_gap_device_name();
    rsp.name = (const uint8_t *)name;
    rsp.name_len = strlen(name);
    rsp.name_is_complete = 1;
    ble_gap_adv_set_fields(&adv);
    ble_gap_adv_rsp_set_fields(&rsp);

    struct ble_gap_adv_params params = {
        .conn_mode = BLE_GAP_CONN_MODE_UND,
        .disc_mode = BLE_GAP_DISC_MODE_GEN,
        .itvl_min = BLE_GAP_ADV_ITVL_MS(100),
        .itvl_max = BLE_GAP_ADV_ITVL_MS(150),
    };
    ble_gap_adv_stop();
    int rc = ble_gap_adv_start(s_own_addr_type, NULL, s_adv_seconds * 1000, &params, on_gap, NULL);
    s_advertising = rc == 0;
    if (rc != 0) {
        ESP_LOGE(TAG, "adv start failed: %d", rc);
    }
}

static int on_gap(struct ble_gap_event *ev, void *arg)
{
    switch (ev->type) {
    case BLE_GAP_EVENT_CONNECT:
        s_advertising = false;
        if (ev->connect.status != 0) {
            start_advertising();
            break;
        }
        s_conn = ev->connect.conn_handle;
        touch();
        /* Ask for a short interval, long packets and the 2M PHY: about 4x the default throughput. */
        struct ble_gap_upd_params fast = {
            .itvl_min = BLE_GAP_CONN_ITVL_MS(15), .itvl_max = BLE_GAP_CONN_ITVL_MS(30),
            .latency = 0, .supervision_timeout = BLE_GAP_SUPERVISION_TIMEOUT_MS(4000),
        };
        ble_gap_update_params(s_conn, &fast);
        ble_gap_set_data_len(s_conn, 251, 2120);
        ble_gap_set_prefered_le_phy(s_conn, BLE_GAP_LE_PHY_2M_MASK, BLE_GAP_LE_PHY_2M_MASK, 0);
        break;
    case BLE_GAP_EVENT_DISCONNECT:
        s_conn = BLE_HS_CONN_HANDLE_NONE;
        s_abort = true;
        break;
    case BLE_GAP_EVENT_ADV_COMPLETE:
        s_advertising = false;
        break;
    case BLE_GAP_EVENT_REPEAT_PAIRING: {
        /* The phone forgot the bond but we kept it: drop ours and let it pair again. */
        struct ble_gap_conn_desc desc;
        if (ble_gap_conn_find(ev->repeat_pairing.conn_handle, &desc) == 0) {
            ble_store_util_delete_peer(&desc.peer_id_addr);
        }
        return BLE_GAP_REPEAT_PAIRING_RETRY;
    }
    default:
        break;
    }
    return 0;
}

static void on_sync(void)
{
    ble_hs_util_ensure_addr(0);
    ble_hs_id_infer_auto(0, &s_own_addr_type);
    start_advertising();
}

static void host_task(void *arg)
{
    nimble_port_run();
    nimble_port_freertos_deinit();
}

/* ---- public ---------------------------------------------------------------------- */
void ble_xfer_start(void)
{
    s_queue = xQueueCreate(2, sizeof(cmd_t));
    ESP_ERROR_CHECK(nimble_port_init());
    ble_hs_cfg.sync_cb = on_sync;
    ble_hs_cfg.store_status_cb = ble_store_util_status_rr;
    ble_hs_cfg.sm_io_cap = BLE_HS_IO_NO_INPUT_OUTPUT;   /* "Just Works" pairing: no display, no keys */
    ble_hs_cfg.sm_bonding = 1;
    ble_hs_cfg.sm_sc = 1;
    ble_hs_cfg.sm_our_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;
    ble_hs_cfg.sm_their_key_dist = BLE_SM_PAIR_KEY_DIST_ENC | BLE_SM_PAIR_KEY_DIST_ID;

    ble_svc_gap_init();
    ble_svc_gatt_init();
    ESP_ERROR_CHECK(ble_gatts_count_cfg(services));
    ESP_ERROR_CHECK(ble_gatts_add_svcs(services));

    uint8_t mac[6];
    char name[20];
    esp_read_mac(mac, ESP_MAC_BT);
    snprintf(name, sizeof(name), DEVICE_NAME "-%02X%02X", mac[4], mac[5]);
    ble_svc_gap_device_name_set(name);
    ble_store_config_init();

    xTaskCreate(transfer_task, "xfer", 4096, NULL, 5, NULL);
    nimble_port_freertos_init(host_task);
}

void ble_xfer_advertise(int seconds)
{
    s_adv_seconds = seconds;
    if (ble_hs_synced()) {
        start_advertising();
    }
}

bool ble_xfer_connected(void)
{
    return s_conn != BLE_HS_CONN_HANDLE_NONE;
}

bool ble_xfer_advertising(void)
{
    return s_advertising;
}

uint32_t ble_xfer_idle_ms(void)
{
    return (uint32_t)((esp_timer_get_time() - s_last_activity_us) / 1000);
}

void ble_xfer_set_battery(uint8_t percent, uint16_t millivolts)
{
    s_battery_mv = millivolts;
    if (percent != s_battery_pct) {
        s_battery_pct = percent;
        if (s_conn != BLE_HS_CONN_HANDLE_NONE) {
            ble_gatts_chr_updated(s_battery_handle);
        }
    }
}

/*
 * panther-abcd-tx: one-frame, raw Ethernet sender for Project A.
 *
 * Safety contract:
 * - interface is mandatory; no default interface and no loopback;
 * - reads only sysfs ifindex/address/flags;
 * - refuses an administratively DOWN interface;
 * - never changes interface flags, addresses, routes, or services;
 * - sends exactly one Ethernet-II broadcast frame, EtherType 0x88b5;
 * - send success proves only the userspace A boundary, never wire delivery.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define ETHERTYPE_ABCD 0x88b5u
#define ETH_HEADER_LEN 14u
#define PAYLOAD_LEN 50u
#define FRAME_LEN (ETH_HEADER_LEN + PAYLOAD_LEN)
#define DIGEST_LEN 32u
#define RUN_ID_LEN 4u
#define SHA_BLOCK 64u

struct sha256_ctx {
    uint32_t h[8];
    uint64_t bit_count;
    uint8_t block[SHA_BLOCK];
    size_t used;
};

static const uint32_t sha_k[64] = {
    0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,
    0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
    0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,
    0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
    0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,
    0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
    0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,
    0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
    0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,
    0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
    0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,
    0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
    0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,
    0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
    0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,
    0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};

static uint32_t rotr32(uint32_t x, unsigned n)
{
    return (x >> n) | (x << (32u - n));
}

static uint32_t load_be32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void store_be32(uint8_t *p, uint32_t v)
{
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

static void sha256_transform(struct sha256_ctx *ctx, const uint8_t block[64])
{
    uint32_t w[64], a, b, c, d, e, f, g, h;
    unsigned i;

    for (i = 0; i < 16; i++)
        w[i] = load_be32(block + (i * 4u));
    for (i = 16; i < 64; i++) {
        uint32_t s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^
                           (w[i - 15] >> 3);
        uint32_t s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^
                           (w[i - 2] >> 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;
    }

    a = ctx->h[0]; b = ctx->h[1]; c = ctx->h[2]; d = ctx->h[3];
    e = ctx->h[4]; f = ctx->h[5]; g = ctx->h[6]; h = ctx->h[7];

    for (i = 0; i < 64; i++) {
        uint32_t s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        uint32_t ch = (e & f) ^ ((~e) & g);
        uint32_t t1 = h + s1 + ch + sha_k[i] + w[i];
        uint32_t s0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
        uint32_t t2 = s0 + maj;

        h = g; g = f; f = e; e = d + t1;
        d = c; c = b; b = a; a = t1 + t2;
    }

    ctx->h[0] += a; ctx->h[1] += b; ctx->h[2] += c; ctx->h[3] += d;
    ctx->h[4] += e; ctx->h[5] += f; ctx->h[6] += g; ctx->h[7] += h;
}

static void sha256_init(struct sha256_ctx *ctx)
{
    static const uint32_t initial[8] = {
        0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
        0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u
    };
    memcpy(ctx->h, initial, sizeof(initial));
    ctx->bit_count = 0;
    ctx->used = 0;
}

static void sha256_update(struct sha256_ctx *ctx, const uint8_t *data, size_t len)
{
    size_t take;

    ctx->bit_count += (uint64_t)len * 8u;
    while (len != 0) {
        take = SHA_BLOCK - ctx->used;
        if (take > len)
            take = len;
        memcpy(ctx->block + ctx->used, data, take);
        ctx->used += take;
        data += take;
        len -= take;
        if (ctx->used == SHA_BLOCK) {
            sha256_transform(ctx, ctx->block);
            ctx->used = 0;
        }
    }
}

static void sha256_final(struct sha256_ctx *ctx, uint8_t out[32])
{
    uint64_t bits = ctx->bit_count;
    unsigned i;

    ctx->block[ctx->used++] = 0x80u;
    if (ctx->used > 56u) {
        memset(ctx->block + ctx->used, 0, SHA_BLOCK - ctx->used);
        sha256_transform(ctx, ctx->block);
        ctx->used = 0;
    }
    memset(ctx->block + ctx->used, 0, 56u - ctx->used);
    for (i = 0; i < 8; i++)
        ctx->block[63u - i] = (uint8_t)(bits >> (i * 8u));
    sha256_transform(ctx, ctx->block);

    for (i = 0; i < 8; i++)
        store_be32(out + (i * 4u), ctx->h[i]);
}

static void sha256(const uint8_t *data, size_t len, uint8_t out[32])
{
    struct sha256_ctx ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, out);
}

static int read_sysfs(const char *ifname, const char *leaf,
                      char *buf, size_t buflen)
{
    char path[256];
    FILE *fp;
    size_t n;

    if (snprintf(path, sizeof(path), "/sys/class/net/%s/%s", ifname, leaf)
        >= (int)sizeof(path)) {
        errno = ENAMETOOLONG;
        return -1;
    }
    fp = fopen(path, "r");
    if (fp == NULL)
        return -1;
    n = fread(buf, 1, buflen - 1u, fp);
    if (ferror(fp)) {
        int saved = errno != 0 ? errno : EIO;
        fclose(fp);
        errno = saved;
        return -1;
    }
    if (fclose(fp) != 0)
        return -1;
    buf[n] = '\0';
    while (n > 0 && (buf[n - 1] == '\n' || buf[n - 1] == '\r'))
        buf[--n] = '\0';
    if (n == 0) {
        errno = EIO;
        return -1;
    }
    return 0;
}

static int parse_mac(const char *s, uint8_t mac[6])
{
    unsigned int v[6];
    char tail;

    if (sscanf(s, "%2x:%2x:%2x:%2x:%2x:%2x%c",
               &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &tail) != 6)
        return -1;
    for (unsigned i = 0; i < 6; i++) {
        if (v[i] > 255u)
            return -1;
        mac[i] = (uint8_t)v[i];
    }
    return 0;
}

static int parse_run_id(const char *s, uint8_t out[4])
{
    if (strlen(s) != 8u)
        return -1;
    for (unsigned i = 0; i < 4; i++) {
        char pair[3] = { s[i * 2u], s[i * 2u + 1u], '\0' };
        char *end = NULL;
        unsigned long v;
        errno = 0;
        v = strtoul(pair, &end, 16);
        if (errno != 0 || end == pair || *end != '\0' || v > 255u)
            return -1;
        out[i] = (uint8_t)v;
    }
    return 0;
}

static int parse_sequence(const char *s, uint64_t *value)
{
    char *end = NULL;
    unsigned long long v;

    errno = 0;
    v = strtoull(s, &end, 0);
    if (errno != 0 || end == s || *end != '\0')
        return -1;
    *value = (uint64_t)v;
    return 0;
}

static void print_hex(const char *name, const uint8_t *data, size_t len)
{
    printf("%s=", name);
    for (size_t i = 0; i < len; i++)
        printf("%02x", data[i]);
    putchar('\n');
}

static void build_frame(uint8_t frame[FRAME_LEN], const uint8_t src[6],
                        const uint8_t run_id[4], uint64_t sequence)
{
    uint8_t *payload = frame + ETH_HEADER_LEN;
    uint8_t digest[DIGEST_LEN];

    memset(frame, 0xff, 6);
    memcpy(frame + 6, src, 6);
    frame[12] = (uint8_t)(ETHERTYPE_ABCD >> 8);
    frame[13] = (uint8_t)ETHERTYPE_ABCD;

    memcpy(payload, "ABCD", 4);
    memcpy(payload + 4, run_id, RUN_ID_LEN);
    for (unsigned i = 0; i < 8; i++)
        payload[8u + i] = (uint8_t)(sequence >> ((7u - i) * 8u));
    payload[16] = 0;
    payload[17] = DIGEST_LEN;
    sha256(payload, 18, digest);
    memcpy(payload + 18, digest, DIGEST_LEN);
}

static int self_test(void)
{
    static const uint8_t expected[32] = {
        0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,
        0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,
        0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,
        0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad
    };
    uint8_t got[32], run_id[4] = { 0, 1, 2, 3 };
    uint8_t src[6] = { 2, 0, 0, 0, 0, 1 };
    uint8_t frame[FRAME_LEN];

    sha256((const uint8_t *)"abc", 3, got);
    if (memcmp(got, expected, sizeof(expected)) != 0) {
        puts("sha256_test=FAIL");
        return 1;
    }
    build_frame(frame, src, run_id, 1);
    if (sizeof(frame) != 64u || frame[12] != 0x88u || frame[13] != 0xb5u ||
        memcmp(frame + ETH_HEADER_LEN, "ABCD", 4) != 0 ||
        frame[ETH_HEADER_LEN + 17u] != 32u) {
        puts("frame_test=FAIL");
        return 1;
    }
    puts("sha256_test=PASS");
    puts("frame_test=PASS");
    puts("frame_len=64");
    puts("self_test=PASS");
    return 0;
}

static void usage(const char *name)
{
    fprintf(stderr,
        "usage: %s --interface IFACE --run-id 8HEX --sequence UINT64\n"
        "       %s --self-test\n", name, name);
}

int main(int argc, char **argv)
{
    const char *ifname = NULL, *run_text = NULL, *seq_text = NULL;
    char index_text[32], address_text[64], flags_text[32];
    uint8_t run_id[4], src_mac[6], frame[FRAME_LEN];
    uint64_t sequence;
    unsigned long ifindex_value, flags_value;
    char *end = NULL;
    int fd, rc, saved_errno;
    struct sockaddr_ll sll;
    ssize_t sent;

    if (argc == 2 && strcmp(argv[1], "--self-test") == 0)
        return self_test();

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--interface") == 0 && i + 1 < argc)
            ifname = argv[++i];
        else if (strcmp(argv[i], "--run-id") == 0 && i + 1 < argc)
            run_text = argv[++i];
        else if (strcmp(argv[i], "--sequence") == 0 && i + 1 < argc)
            seq_text = argv[++i];
        else {
            usage(argv[0]);
            return 2;
        }
    }

    if (ifname == NULL || run_text == NULL || seq_text == NULL ||
        ifname[0] == '\0' || strlen(ifname) >= 64u ||
        strchr(ifname, '/') != NULL || strcmp(ifname, ".") == 0 ||
        strcmp(ifname, "..") == 0 ||
        parse_run_id(run_text, run_id) != 0 ||
        parse_sequence(seq_text, &sequence) != 0) {
        usage(argv[0]);
        return 2;
    }

    if (read_sysfs(ifname, "ifindex", index_text, sizeof(index_text)) != 0 ||
        read_sysfs(ifname, "address", address_text, sizeof(address_text)) != 0 ||
        read_sysfs(ifname, "flags", flags_text, sizeof(flags_text)) != 0) {
        fprintf(stderr, "interface_read_error=%s\n", strerror(errno));
        return 1;
    }

    errno = 0;
    ifindex_value = strtoul(index_text, &end, 10);
    if (errno != 0 || end == index_text || *end != '\0' ||
        ifindex_value == 0 || ifindex_value > 0x7fffffffUL ||
        parse_mac(address_text, src_mac) != 0) {
        fprintf(stderr, "interface_metadata_error=invalid_sysfs_value\n");
        return 1;
    }

    errno = 0;
    flags_value = strtoul(flags_text, &end, 0);
    if (errno != 0 || end == flags_text || *end != '\0') {
        fprintf(stderr, "interface_flags_error=invalid_sysfs_value\n");
        return 1;
    }
    if ((flags_value & 0x1UL) == 0) {
        fprintf(stderr, "interface_state=DOWN\n");
        fprintf(stderr, "action=refuse_without_changing_interface\n");
        return 1;
    }
    if ((flags_value & 0x8UL) != 0) {
        fprintf(stderr, "interface_type=LOOPBACK\n");
        fprintf(stderr, "action=refuse_loopback\n");
        return 1;
    }

    build_frame(frame, src_mac, run_id, sequence);

    printf("tool=panther-abcd-tx\n");
    printf("interface=%s\n", ifname);
    printf("ifindex=%lu\n", ifindex_value);
    printf("ifflags=0x%lx\n", flags_value);
    print_hex("source_mac", src_mac, sizeof(src_mac));
    puts("destination_mac=ffffffffffff");
    puts("ethertype=88b5");
    print_hex("run_id", run_id, sizeof(run_id));
    printf("sequence=%llu\n", (unsigned long long)sequence);
    printf("payload_len=%u\n", DIGEST_LEN);
    printf("frame_len=%u\n", FRAME_LEN);
    print_hex("payload_digest", frame + ETH_HEADER_LEN + 18u, DIGEST_LEN);
    print_hex("frame_hex", frame, sizeof(frame));

    fd = socket(AF_PACKET, SOCK_RAW, htons(ETHERTYPE_ABCD));
    if (fd < 0) {
        saved_errno = errno;
        fprintf(stderr, "socket_rc=-1\nsocket_errno=%d\nsocket_error=%s\n",
                saved_errno, strerror(saved_errno));
        return 1;
    }

    memset(&sll, 0, sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_protocol = htons(ETHERTYPE_ABCD);
    sll.sll_ifindex = (int)ifindex_value;
    sll.sll_halen = ETH_ALEN;
    memset(sll.sll_addr, 0xff, ETH_ALEN);

    rc = bind(fd, (struct sockaddr *)&sll, sizeof(sll));
    if (rc < 0) {
        saved_errno = errno;
        fprintf(stderr, "bind_rc=-1\nbind_errno=%d\nbind_error=%s\n",
                saved_errno, strerror(saved_errno));
        close(fd);
        return 1;
    }

    sent = sendto(fd, frame, sizeof(frame), 0,
                  (struct sockaddr *)&sll, sizeof(sll));
    saved_errno = sent < 0 ? errno : 0;
    printf("sendto_rc=%ld\n", (long)sent);
    printf("sendto_errno=%d\n", saved_errno);
    if (saved_errno != 0)
        printf("sendto_error=%s\n", strerror(saved_errno));
    close(fd);

    if (sent != (ssize_t)sizeof(frame)) {
        puts("boundary_A=FAIL");
        return 1;
    }
    puts("boundary_A=PASS");
    puts("wire_delivery=NOT_VERIFIED");
    return 0;
}

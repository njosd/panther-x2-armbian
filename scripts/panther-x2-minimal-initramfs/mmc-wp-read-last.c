/*
 * Read-only eMMC last write-protect-group audit helper.
 *
 * This program issues only:
 *   CMD8  SEND_EXT_CSD (read 512 bytes)
 *   CMD31 SEND_WRITE_PROT_TYPE (read 8 bytes)
 *
 * It never issues CMD6, CMD28, CMD29 or any data-write command.
 * The target is accepted only when MMC type, DF4032 name and exact CID match.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <linux/fs.h>
#include <linux/mmc/ioctl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

#define MMC_SEND_EXT_CSD 8
#define MMC_SEND_WRITE_PROT_TYPE 31
#define MMC_RSP_PRESENT (1U << 0)
#define MMC_RSP_CRC     (1U << 2)
#define MMC_RSP_OPCODE  (1U << 4)
#define MMC_CMD_ADTC    (1U << 5)
#define EXT_CSD_HC_WP_GRP_SIZE 221
#define EXT_CSD_HC_ERASE_GRP_SIZE 224
#define EXT_CSD_SEC_COUNT_0 212
#define EXT_CSD_SEC_COUNT_1 213
#define EXT_CSD_SEC_COUNT_2 214
#define EXT_CSD_SEC_COUNT_3 215
#define EXT_CSD_ERASE_GROUP_DEF 175
#define EXT_CSD_REV 192
#define WP_GROUPS_PER_CMD31 32

static int read_text(const char *path, char *buf, size_t size)
{
    FILE *f = fopen(path, "r");
    size_t n;
    if (!f)
        return -1;
    if (!fgets(buf, (int)size, f)) {
        fclose(f);
        return -1;
    }
    fclose(f);
    n = strlen(buf);
    while (n && (buf[n - 1] == '\n' || buf[n - 1] == '\r' || buf[n - 1] == ' ' || buf[n - 1] == '\t'))
        buf[--n] = '\0';
    return 0;
}

static int mmc_read_cmd(int fd, unsigned int opcode, uint32_t arg,
                        unsigned int block_size, unsigned int blocks,
                        void *data)
{
    struct mmc_ioc_cmd cmd;
    memset(&cmd, 0, sizeof(cmd));
    cmd.opcode = opcode;
    cmd.arg = arg;
    cmd.flags = MMC_RSP_PRESENT | MMC_RSP_CRC | MMC_RSP_OPCODE | MMC_CMD_ADTC;
    cmd.blksz = block_size;
    cmd.blocks = blocks;
    cmd.write_flag = 0;
    cmd.data_ptr = (uintptr_t)data;
    cmd.cmd_timeout_ms = 2000;
    return ioctl(fd, MMC_IOC_CMD, &cmd);
}

static int verify_target(const char *device, const char *expected_cid)
{
    char name[64], path[256], value[128];
    size_t i;

    if (strncmp(device, "/dev/mmcblk", 11) != 0 || !device[11])
        return -1;
    for (i = 11; device[i]; i++) {
        if (device[i] < '0' || device[i] > '9')
            return -1;
    }
    if (snprintf(name, sizeof(name), "%s", device + 5) >= (int)sizeof(name))
        return -1;

    if (snprintf(path, sizeof(path), "/sys/class/block/%s/device/type", name) >= (int)sizeof(path) ||
        read_text(path, value, sizeof(value)) || strcmp(value, "MMC") != 0) {
        fprintf(stderr, "Refusing target: sysfs device type is not MMC\n");
        return -1;
    }
    if (snprintf(path, sizeof(path), "/sys/class/block/%s/device/name", name) >= (int)sizeof(path) ||
        read_text(path, value, sizeof(value)) || strcmp(value, "DF4032") != 0) {
        fprintf(stderr, "Refusing target: eMMC name is not DF4032\n");
        return -1;
    }
    if (snprintf(path, sizeof(path), "/sys/class/block/%s/device/cid", name) >= (int)sizeof(path) ||
        read_text(path, value, sizeof(value)) || strcmp(value, expected_cid) != 0) {
        fprintf(stderr, "Refusing target: CID does not match the expected DF4032 eMMC\n");
        return -1;
    }
    printf("Target identity verified: %s type=MMC name=DF4032 CID=%s\n", device, value);
    return 0;
}

int main(int argc, char **argv)
{
    const char *device, *expected_cid;
    uint8_t ext_csd[512] = {0}, data[8] = {0};
    uint64_t bytes, sectors, bits = 0;
    uint32_t sec_count, wp_group_size, group_count, last_group;
    uint32_t query_first_group, query_lba;
    uint32_t offset, status;
    int fd, i;

    if (argc != 3) {
        fprintf(stderr, "Usage: %s /dev/mmcblkN EXPECTED_CID\n", argv[0]);
        return 2;
    }
    device = argv[1];
    expected_cid = argv[2];

    if (verify_target(device, expected_cid))
        return 1;

    fd = open(device, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        perror("open eMMC");
        return 1;
    }

    if (mmc_read_cmd(fd, MMC_SEND_EXT_CSD, 0, 512, 1, ext_csd)) {
        perror("CMD8 SEND_EXT_CSD failed");
        close(fd);
        return 1;
    }

    if (ext_csd[EXT_CSD_REV] < 5 || ext_csd[EXT_CSD_ERASE_GROUP_DEF] != 1) {
        fprintf(stderr, "Unsupported EXT_CSD revision or HC erase-group definition\n");
        close(fd);
        return 1;
    }

    sec_count = ((uint32_t)ext_csd[EXT_CSD_SEC_COUNT_3] << 24) |
                ((uint32_t)ext_csd[EXT_CSD_SEC_COUNT_2] << 16) |
                ((uint32_t)ext_csd[EXT_CSD_SEC_COUNT_1] << 8) |
                (uint32_t)ext_csd[EXT_CSD_SEC_COUNT_0];
    wp_group_size = (uint32_t)ext_csd[EXT_CSD_HC_ERASE_GRP_SIZE] *
                    (uint32_t)ext_csd[EXT_CSD_HC_WP_GRP_SIZE] * 1024U;

    if (!wp_group_size || ioctl(fd, BLKGETSIZE64, &bytes) || bytes % 512) {
        perror("eMMC capacity/WP group query failed");
        close(fd);
        return 1;
    }
    sectors = bytes / 512;
    if (sectors != sec_count) {
        fprintf(stderr, "Refusing: BLKGETSIZE64 sectors (%" PRIu64 ") != EXT_CSD SEC_COUNT (%" PRIu32 ")\n",
                sectors, sec_count);
        close(fd);
        return 1;
    }

    group_count = (uint32_t)((sectors + wp_group_size - 1) / wp_group_size);
    if (!group_count) {
        fprintf(stderr, "Invalid WP group count\n");
        close(fd);
        return 1;
    }
    last_group = group_count - 1;
    query_first_group = (last_group / WP_GROUPS_PER_CMD31) * WP_GROUPS_PER_CMD31;
    if ((uint64_t)query_first_group * wp_group_size >= sectors) {
        fprintf(stderr, "Refusing: computed CMD31 address outside eMMC capacity\n");
        close(fd);
        return 1;
    }
    query_lba = query_first_group * wp_group_size;

    printf("EXT_CSD revision=%u SEC_COUNT=%" PRIu32 " sectors\n",
           ext_csd[EXT_CSD_REV], sec_count);
    printf("HC_ERASE_GRP_SIZE=%u HC_WP_GRP_SIZE=%u WP_group=%" PRIu32 " sectors (%" PRIu32 " bytes)\n",
           ext_csd[EXT_CSD_HC_ERASE_GRP_SIZE], ext_csd[EXT_CSD_HC_WP_GRP_SIZE],
           wp_group_size, wp_group_size * 512U);
    printf("USER_WP=0x%02x BOOT_WP=0x%02x BOOT_WP_STATUS=0x%02x\n",
           ext_csd[171], ext_csd[173], ext_csd[174]);
    printf("Capacity=%" PRIu64 " sectors; addressable WP groups=%" PRIu32
           "; last group=%" PRIu32 "; last group start LBA=%" PRIu64 "\n",
           sectors, group_count, last_group, (uint64_t)last_group * wp_group_size);
    printf("Issuing read-only CMD31 at LBA=%" PRIu32 " for groups %u..%u\n",
           query_lba, query_first_group, query_first_group + 31);

    if (mmc_read_cmd(fd, MMC_SEND_WRITE_PROT_TYPE, query_lba, 8, 1, data)) {
        perror("CMD31 SEND_WRITE_PROT_TYPE failed");
        close(fd);
        return 1;
    }

    for (i = 0; i < 8; i++)
        bits = (bits << 8) | data[i];

    offset = last_group - query_first_group;
    status = (uint32_t)((bits >> (offset * 2)) & 0x3U);
    printf("CMD31 payload=");
    for (i = 0; i < 8; i++)
        printf("%02x", data[i]);
    printf("\nLast WP group %u status=%u: ", last_group, status);
    switch (status) {
    case 0: puts("No write protection"); break;
    case 1: puts("Temporary write protection"); break;
    case 2: puts("Power-on write protection"); break;
    case 3: puts("Permanent write protection"); break;
    default: puts("Unknown"); break;
    }

    puts("Read-only audit complete: only CMD8 and CMD31 were issued; no CMD6/CMD28/CMD29 or data-write command.");
    close(fd);
    return 0;
}

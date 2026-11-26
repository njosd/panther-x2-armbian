/*
 * Panther X2 B2-1 R3 RK809 identity-only I2C probe.
 *
 * Fixed scope:
 *   adapter: /dev/i2c-0 (major 89, minor 0)
 *   7-bit address: 0x20
 *   registers: 0xED (PMIC_CHIP_NAME), 0xEE (PMIC_CHIP_VER)
 *
 * Each read uses one I2C_RDWR ioctl containing a register-index message
 * followed by a one-byte read message (repeated START). No bus scan,
 * I2C_SLAVE selection, PMIC data-register write, driver binding, regulator
 * operation, or power-state operation is performed.
 *
 * If /dev/i2c-0 is absent, the program creates only that character-device
 * node (89:0, mode 0600) under the current /dev. In the R1 initramfs this
 * is a RAM-rootfs change and disappears on reboot.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <sys/types.h>
#include <unistd.h>

#define I2C_NODE "/dev/i2c-0"
#define I2C_MAJOR 89
#define I2C_MINOR 0
#define RK809_ADDR 0x20

static int ensure_i2c_node(void)
{
    struct stat st;

    if (lstat(I2C_NODE, &st) == 0) {
        if (!S_ISCHR(st.st_mode) ||
            major(st.st_rdev) != I2C_MAJOR ||
            minor(st.st_rdev) != I2C_MINOR) {
            fprintf(stderr,
                    "node_check=FAIL existing /dev/i2c-0 is not char 89:0\n");
            return -1;
        }
        puts("node_action=EXISTING_CORRECT_CHAR_DEVICE");
        return 0;
    }

    if (errno != ENOENT) {
        fprintf(stderr, "node_lstat_errno=%d (%s)\n",
                errno, strerror(errno));
        return -1;
    }

    if (mknodat(AT_FDCWD, I2C_NODE,
                S_IFCHR | S_IRUSR | S_IWUSR,
                makedev(I2C_MAJOR, I2C_MINOR)) < 0) {
        fprintf(stderr, "node_mknodat_errno=%d (%s)\n",
                errno, strerror(errno));
        return -1;
    }

    puts("node_action=CREATED_TEMPORARY_CHAR_DEVICE_89_0");
    return 0;
}

static int read_register(int fd, unsigned char reg, unsigned char *value)
{
    struct i2c_msg msgs[2];
    struct i2c_rdwr_ioctl_data request;
    unsigned char reg_index = reg;
    unsigned char data = 0;
    int rc;
    int saved_errno;

    memset(msgs, 0, sizeof(msgs));
    msgs[0].addr = RK809_ADDR;
    msgs[0].flags = 0;
    msgs[0].len = 1;
    msgs[0].buf = &reg_index;

    msgs[1].addr = RK809_ADDR;
    msgs[1].flags = I2C_M_RD;
    msgs[1].len = 1;
    msgs[1].buf = &data;

    request.msgs = msgs;
    request.nmsgs = 2;

    errno = 0;
    rc = ioctl(fd, I2C_RDWR, &request);
    saved_errno = rc < 0 ? errno : 0;

    printf("read_reg_0x%02X_ioctl_rc=%d\n", reg, rc);
    printf("read_reg_0x%02X_errno=%d\n", reg, saved_errno);
    if (saved_errno)
        printf("read_reg_0x%02X_error=%s\n",
               reg, strerror(saved_errno));

    if (rc != 2)
        return -1;

    *value = data;
    printf("read_reg_0x%02X_value=0x%02X\n", reg, data);
    return 0;
}

int main(int argc, char **argv)
{
    int fd;
    unsigned long funcs = 0;
    unsigned char chip_name = 0;
    unsigned char chip_ver = 0;
    int name_rc;
    int ver_rc;

    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        puts("probe=self-test");
        puts("architecture=aarch64");
        puts("scope=RK809_ID_REGISTERS_ONLY");
        puts("self_test=PASS");
        return 0;
    }
    if (argc != 1) {
        fprintf(stderr, "usage: %s [--self-test]\n", argv[0]);
        return 2;
    }

    puts("probe=panther-x2-b2-1-r3-rk809-id-ro");
    printf("euid=%u\n", (unsigned)geteuid());
    printf("adapter=%s\n", I2C_NODE);
    printf("adapter_dev=%u:%u\n", I2C_MAJOR, I2C_MINOR);
    printf("target_address=0x%02X\n", RK809_ADDR);
    puts("target_registers=0xED,0xEE");
    puts("write_policy=NO_PMIC_DATA_REGISTER_WRITES");
    puts("transfer_policy=I2C_RDWR_TWO_MESSAGES_REPEATED_START");

    if (geteuid() != 0) {
        puts("privilege_check=FAIL_ROOT_REQUIRED");
        return 1;
    }

    if (ensure_i2c_node() < 0)
        return 1;

    fd = open(I2C_NODE, O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        printf("adapter_open_errno=%d (%s)\n", errno, strerror(errno));
        return 1;
    }
    puts("adapter_open=PASS");

    if (ioctl(fd, I2C_FUNCS, &funcs) < 0) {
        printf("i2c_funcs_errno=%d (%s)\n", errno, strerror(errno));
        close(fd);
        return 1;
    }
    printf("i2c_funcs=0x%lx\n", funcs);
    if (!(funcs & I2C_FUNC_I2C)) {
        puts("i2c_func_i2c=UNSUPPORTED");
        close(fd);
        return 1;
    }
    puts("i2c_func_i2c=SUPPORTED");

    name_rc = read_register(fd, 0xED, &chip_name);
    ver_rc = read_register(fd, 0xEE, &chip_ver);

    printf("rk809_name_read=%s\n", name_rc == 0 ? "PASS" : "FAIL");
    printf("rk809_version_read=%s\n", ver_rc == 0 ? "PASS" : "FAIL");
    if (name_rc == 0 && ver_rc == 0) {
        printf("rk809_id_raw=0x%02X%02X\n", chip_name, chip_ver);
        puts("datasheet_expected_name=0x80");
        puts("datasheet_expected_version=0x92");
        printf("identity_matches_datasheet=%s\n",
               (chip_name == 0x80 && chip_ver == 0x92) ? "YES" : "NO");
    }

    close(fd);
    return (name_rc == 0 && ver_rc == 0) ? 0 : 1;
}

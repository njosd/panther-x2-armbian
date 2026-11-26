/*
 * Panther X2 B2-1 R3.7 RK809 read-only status-register probe.
 *
 * Fixed and exhaustive hardware access scope:
 *   I2C adapter: /dev/i2c-0 (major 89, minor 0)
 *   7-bit target: 0x20
 *   register reads, exactly once each: 0xF0 (PMIC_SYS_STS), 0xF6 (PMIC_OFF_SOURCE)
 *
 * Each access is one I2C_RDWR ioctl with a register-index message followed
 * by a one-byte read message (repeated START). No bus scan, no other register
 * access, no PMIC data-register write, no driver binding, no regulator API,
 * and no power-state operation.
 *
 * If absent, only /dev/i2c-0 char device 89:0 is created in the current /dev.
 * In the dedicated R1 initramfs this is a temporary RAM-rootfs node.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
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
            puts("node_check=FAIL_NOT_CHAR_89_0");
            return -1;
        }
        puts("node_action=EXISTING_CORRECT_CHAR_DEVICE");
        return 0;
    }
    if (errno != ENOENT) {
        printf("node_lstat_errno=%d (%s)\n", errno, strerror(errno));
        return -1;
    }
    if (mknodat(AT_FDCWD, I2C_NODE, S_IFCHR | S_IRUSR | S_IWUSR,
                makedev(I2C_MAJOR, I2C_MINOR)) < 0) {
        printf("node_mknodat_errno=%d (%s)\n", errno, strerror(errno));
        return -1;
    }
    puts("node_action=CREATED_TEMPORARY_CHAR_DEVICE_89_0");
    return 0;
}

static int read_one_ro_register(int fd, unsigned char reg,
                                const char *name, unsigned char *value)
{
    struct i2c_msg msgs[2];
    struct i2c_rdwr_ioctl_data request;
    unsigned char index = reg;
    unsigned char data = 0;
    int rc, saved_errno;

    memset(msgs, 0, sizeof(msgs));
    msgs[0].addr = RK809_ADDR;
    msgs[0].len = 1;
    msgs[0].buf = &index;
    msgs[1].addr = RK809_ADDR;
    msgs[1].flags = I2C_M_RD;
    msgs[1].len = 1;
    msgs[1].buf = &data;
    request.msgs = msgs;
    request.nmsgs = 2;

    errno = 0;
    rc = ioctl(fd, I2C_RDWR, &request);
    saved_errno = rc < 0 ? errno : 0;
    printf("%s_ioctl_rc=%d\n", name, rc);
    printf("%s_errno=%d\n", name, saved_errno);
    if (saved_errno)
        printf("%s_error=%s\n", name, strerror(saved_errno));
    if (rc != 2)
        return -1;
    *value = data;
    printf("%s_value=0x%02X\n", name, data);
    return 0;
}

int main(int argc, char **argv)
{
    int fd, rc_f0, rc_f6;
    unsigned long funcs = 0;
    unsigned char sys_sts = 0, off_source = 0;

    if (argc == 2 && strcmp(argv[1], "--self-test") == 0) {
        puts("probe=self-test");
        puts("architecture=aarch64");
        puts("scope=RK809_STATUS_REGISTERS_0xF0_0xF6_ONLY");
        puts("self_test=PASS");
        return 0;
    }
    if (argc != 1) {
        fprintf(stderr, "usage: %s [--self-test]\n", argv[0]);
        return 2;
    }

    puts("probe=panther-x2-b2-1-r3-7-rk809-status-ro");
    printf("euid=%u\n", (unsigned)geteuid());
    printf("adapter=%s\n", I2C_NODE);
    printf("adapter_dev=%u:%u\n", I2C_MAJOR, I2C_MINOR);
    printf("target_address=0x%02X\n", RK809_ADDR);
    puts("target_registers=0xF0,0xF6");
    puts("register_0xF0=PMIC_SYS_STS; documented_access=RO");
    puts("register_0xF6=PMIC_OFF_SOURCE; documented_access=RO");
    puts("read_count=ONE_TRANSACTION_PER_REGISTER");
    puts("write_policy=NO_PMIC_DATA_REGISTER_WRITES");
    puts("transfer_policy=I2C_RDWR_TWO_MESSAGES_REPEATED_START");
    puts("bus_scan=DISABLED");
    puts("driver_binding=DISABLED");
    puts("regulator_api=NOT_USED");

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

    rc_f0 = read_one_ro_register(fd, 0xF0, "read_reg_0xF0", &sys_sts);
    rc_f6 = read_one_ro_register(fd, 0xF6, "read_reg_0xF6", &off_source);
    puts(rc_f0 == 0 ? "pmic_sys_sts_read=PASS" : "pmic_sys_sts_read=FAIL");
    puts(rc_f6 == 0 ? "pmic_off_source_read=PASS" : "pmic_off_source_read=FAIL");
    if (rc_f0 == 0)
        printf("PMIC_SYS_STS_raw=0x%02X\n", sys_sts);
    if (rc_f6 == 0)
        printf("PMIC_OFF_SOURCE_raw=0x%02X\n", off_source);
    close(fd);
    return (rc_f0 == 0 && rc_f6 == 0) ? 0 : 1;
}

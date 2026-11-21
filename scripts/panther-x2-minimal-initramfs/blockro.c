#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fs.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    int fd, ro = 1, actual = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: blockro /dev/block-device\n");
        return 2;
    }

    fd = open(argv[1], O_RDONLY | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "blockro: open %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    if (ioctl(fd, BLKROSET, &ro) < 0) {
        fprintf(stderr, "blockro: BLKROSET %s: %s\n", argv[1], strerror(errno));
        close(fd);
        return 1;
    }

    if (ioctl(fd, BLKROGET, &actual) < 0 || actual != 1) {
        fprintf(stderr, "blockro: read-only verification failed for %s\n", argv[1]);
        close(fd);
        return 1;
    }

    printf("%s: ro=%d\n", argv[1], actual);
    close(fd);
    return 0;
}

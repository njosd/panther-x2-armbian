/*
 * Panther X2 B2-1 R1 AF_PACKET runtime probe.
 *
 * This program does not configure an IP address or modify network settings.
 * It exercises AF_PACKET socket creation, binding to an existing interface,
 * raw/datagram send attempts, and optional packet-socket receive observation.
 *
 * Run as root (or with CAP_NET_RAW). A successful send syscall is NOT proof
 * of physical Ethernet transmission. R1 has no physical NIC by design.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/if_ether.h>
#include <linux/if_packet.h>
#include <net/if.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

static void result(const char *name, long rc, int err)
{
    printf("%s_rc=%ld\n", name, rc);
    printf("%s_errno=%d\n", name, err);
    if (err)
        printf("%s_error=%s\n", name, strerror(err));
}

static int self_test(void)
{
    puts("probe=self-test");
    puts("architecture=aarch64");
    puts("self_test=PASS");
    return 0;
}

int main(int argc, char **argv)
{
    const char *ifname = "lo";
    char ifindex_path[128];
    char ifindex_text[32];
    struct sockaddr_ll sll;
    unsigned char raw_frame[ETH_HLEN + 8];
    unsigned char dgram_payload[8] = {
        'P', 'X', '2', '-', 'R', '1', '!', '!'
    };
    int rawfd = -1, rxfd = -1, dgramfd = -1;
    int ifindex = 0;
    int rc, saved_errno;
    int bind_raw_rc, bind_rx_rc, bind_dgram_rc;
    struct pollfd pfd;
    unsigned char rxbuf[256];

    if (argc == 2 && strcmp(argv[1], "--self-test") == 0)
        return self_test();
    if (argc > 2) {
        fprintf(stderr, "usage: %s [interface]\n", argv[0]);
        return 2;
    }
    if (argc == 2)
        ifname = argv[1];

    printf("probe=panther-x2-r1-af-packet\n");
    printf("interface=%s\n", ifname);
    printf("uid=%u\n", (unsigned)getuid());
    printf("euid=%u\n", (unsigned)geteuid());

    memset(&ifr, 0, sizeof(ifr));
    if (strlen(ifname) >= IFNAMSIZ) {
        puts("ifindex_rc=-1");
        puts("ifindex_errno=EINVAL");
        return 2;
    }
    strcpy(ifr.ifr_name, ifname);

    rawfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    saved_errno = rawfd < 0 ? errno : 0;
    result("socket_raw", rawfd, saved_errno);

    rxfd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    saved_errno = rxfd < 0 ? errno : 0;
    result("socket_rx", rxfd, saved_errno);

    dgramfd = socket(AF_PACKET, SOCK_DGRAM, htons(ETH_P_ALL));
    saved_errno = dgramfd < 0 ? errno : 0;
    result("socket_dgram", dgramfd, saved_errno);

    if (rawfd < 0 || rxfd < 0 || dgramfd < 0)
        goto out;

    snprintf(ifindex_path, sizeof(ifindex_path),
             "/sys/class/net/%s/ifindex", ifname);
    int ifindex_fd = open(ifindex_path, O_RDONLY | O_CLOEXEC);
    if (ifindex_fd < 0) {
        saved_errno = errno;
        result("ifindex_open", -1, saved_errno);
        goto out;
    }
    ssize_t ifindex_len = read(ifindex_fd, ifindex_text,
                               sizeof(ifindex_text) - 1);
    saved_errno = ifindex_len < 0 ? errno : 0;
    result("ifindex_read", ifindex_len, saved_errno);
    close(ifindex_fd);
    if (ifindex_len <= 0)
        goto out;
    ifindex_text[ifindex_len] = '\0';
    char *endptr = NULL;
    long parsed_ifindex = strtol(ifindex_text, &endptr, 10);
    if (endptr == ifindex_text || parsed_ifindex <= 0) {
        puts("ifindex_parse_rc=-1");
        puts("ifindex_parse_errno=EINVAL");
        goto out;
    }
    ifindex = (int)parsed_ifindex;
    printf("ifindex=%d\n", ifindex);

    memset(&sll, 0, sizeof(sll));
    sll.sll_family = AF_PACKET;
    sll.sll_protocol = htons(ETH_P_ALL);
    sll.sll_ifindex = ifindex;

    bind_raw_rc = bind(rawfd, (struct sockaddr *)&sll, sizeof(sll));
    saved_errno = bind_raw_rc < 0 ? errno : 0;
    result("bind_raw", bind_raw_rc, saved_errno);

    bind_rx_rc = bind(rxfd, (struct sockaddr *)&sll, sizeof(sll));
    saved_errno = bind_rx_rc < 0 ? errno : 0;
    result("bind_rx", bind_rx_rc, saved_errno);

    bind_dgram_rc = bind(dgramfd, (struct sockaddr *)&sll, sizeof(sll));
    saved_errno = bind_dgram_rc < 0 ? errno : 0;
    result("bind_dgram", bind_dgram_rc, saved_errno);

    /* A deterministic test frame. Loopback is not an Ethernet device. */
    memset(raw_frame, 0, sizeof(raw_frame));
    memset(raw_frame, 0xff, 6);
    raw_frame[6] = 0x02;
    raw_frame[11] = 0x01;
    raw_frame[12] = 0x88;
    raw_frame[13] = 0xb5;
    memcpy(raw_frame + ETH_HLEN, "PX2R1TX!", 8);

    if (bind_raw_rc == 0) {
        sll.sll_protocol = htons(0x88b5);
        rc = sendto(rawfd, raw_frame, sizeof(raw_frame), 0,
                    (struct sockaddr *)&sll, sizeof(sll));
        saved_errno = rc < 0 ? errno : 0;
        result("send_raw", rc, saved_errno);
    } else {
        puts("send_raw_rc=SKIPPED_BIND_FAILED");
    }

    if (bind_dgram_rc == 0) {
        sll.sll_protocol = htons(0x88b5);
        rc = sendto(dgramfd, dgram_payload, sizeof(dgram_payload), 0,
                    (struct sockaddr *)&sll, sizeof(sll));
        saved_errno = rc < 0 ? errno : 0;
        result("send_dgram", rc, saved_errno);
    } else {
        puts("send_dgram_rc=SKIPPED_BIND_FAILED");
    }

    if (bind_rx_rc == 0) {
        pfd.fd = rxfd;
        pfd.events = POLLIN;
        pfd.revents = 0;
        rc = poll(&pfd, 1, 500);
        saved_errno = rc < 0 ? errno : 0;
        result("poll_rx", rc, saved_errno);
        if (rc > 0 && (pfd.revents & POLLIN)) {
            struct sockaddr_ll from;
            socklen_t fromlen = sizeof(from);
            ssize_t n = recvfrom(rxfd, rxbuf, sizeof(rxbuf), MSG_DONTWAIT,
                                 (struct sockaddr *)&from, &fromlen);
            saved_errno = n < 0 ? errno : 0;
            result("recv_rx", n, saved_errno);
            if (n > 0) {
                printf("recv_packet_type=%u\n", from.sll_pkttype);
                printf("recv_protocol=0x%04x\n", ntohs(from.sll_protocol));
                printf("recv_prefix_hex=");
                for (ssize_t i = 0; i < n && i < 32; i++)
                    printf("%02x", rxbuf[i]);
                putchar('\n');
            }
        } else {
            puts("recv_rx_rc=NO_PACKET_WITHIN_500MS");
        }
    } else {
        puts("poll_rx_rc=SKIPPED_BIND_FAILED");
    }

out:
    if (rawfd >= 0) close(rawfd);
    if (rxfd >= 0) close(rxfd);
    if (dgramfd >= 0) close(dgramfd);
    puts("physical_ethernet_tx=NOT_TESTED");
    return 0;
}

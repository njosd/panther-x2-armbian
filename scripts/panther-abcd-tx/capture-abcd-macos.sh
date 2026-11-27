#!/bin/bash
# Capture exactly the Project-A ABCD EtherType on a macOS interface.
# This script does not change interface, address, route, or service state.
set -u

usage() {
    echo "Usage: $0 <interface> <output.pcap>" >&2
    exit 2
}

[ "$#" -eq 2 ] || usage
IFACE=$1
PCAP=$2

case "$IFACE" in
    ""|*/*|.|..) usage ;;
esac

if ! command -v tcpdump >/dev/null 2>&1; then
    echo "ERROR: tcpdump not found" >&2
    exit 1
fi

if [ -e "$PCAP" ]; then
    echo "ERROR: output already exists; refusing to overwrite: $PCAP" >&2
    exit 1
fi

PARENT=$(dirname "$PCAP")
if [ ! -d "$PARENT" ]; then
    echo "ERROR: output directory does not exist: $PARENT" >&2
    exit 1
fi

echo "capture_interface=$IFACE"
echo "capture_filter=ether proto 0x88b5"
echo "output=$PCAP"
echo "snaplen=full"
echo "No network settings will be changed."
echo "Start the known-good Linux sender now; press Ctrl-C after the test frame appears."
exec sudo tcpdump -i "$IFACE" -nn -s 0 -U -w "$PCAP" 'ether proto 0x88b5'

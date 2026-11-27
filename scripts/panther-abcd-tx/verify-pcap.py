#!/usr/bin/env python3
"""Offline verifier for the Project-A EtherType 0x88b5 ABCD pcap frame."""
import argparse
import hashlib
import struct
import sys
from pathlib import Path

ETHERTYPE = 0x88B5
FRAME_LEN = 64
PAYLOAD_LEN = 50
DIGEST_LEN = 32
MAGIC = b"ABCD"

PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1": ("<", "microseconds"),
    b"\xa1\xb2\xc3\xd4": (">", "microseconds"),
    b"\x4d\x3c\xb2\xa1": ("<", "nanoseconds"),
    b"\xa1\xb2\x3c\x4d": (">", "nanoseconds"),
}


class VerifyError(Exception):
    pass


def parse_pcap(data):
    if len(data) < 24:
        raise VerifyError("pcap_global_header=TRUNCATED")
    magic = data[:4]
    if magic not in PCAP_MAGICS:
        raise VerifyError("pcap_format=UNSUPPORTED_OR_NOT_CLASSIC_PCAP")
    endian, precision = PCAP_MAGICS[magic]
    major, minor, _zone, _sigfigs, snaplen, network = struct.unpack(
        endian + "HHIIII", data[4:24]
    )
    if (major, minor) != (2, 4):
        raise VerifyError(f"pcap_version=UNSUPPORTED_{major}.{minor}")
    if network != 1:
        raise VerifyError(f"link_type=UNSUPPORTED_{network}_EXPECTED_ETHERNET_1")
    if snaplen == 0:
        raise VerifyError("pcap_snaplen=INVALID_ZERO")

    packets = []
    offset = 24
    index = 0
    while offset < len(data):
        if len(data) - offset < 16:
            raise VerifyError(f"packet_record_{index}=TRUNCATED_HEADER")
        ts_sec, ts_frac, incl_len, orig_len = struct.unpack(
            endian + "IIII", data[offset:offset + 16]
        )
        offset += 16
        if incl_len > snaplen or incl_len > len(data) - offset:
            raise VerifyError(f"packet_record_{index}=TRUNCATED_DATA")
        if incl_len > orig_len:
            raise VerifyError(f"packet_record_{index}=INVALID_LENGTHS")
        frame = data[offset:offset + incl_len]
        offset += incl_len
        packets.append((index, ts_sec, ts_frac, frame, incl_len, orig_len))
        index += 1
    return precision, packets


def inspect_frame(frame):
    if len(frame) < 14:
        raise VerifyError("ethernet_header=TRUNCATED")
    ethertype = int.from_bytes(frame[12:14], "big")
    if ethertype != ETHERTYPE:
        return None
    if len(frame) != FRAME_LEN:
        raise VerifyError(f"frame_length={len(frame)}_EXPECTED_{FRAME_LEN}")
    if frame[:6] != b"\xff" * 6:
        raise VerifyError("destination_mac=NOT_BROADCAST")
    payload = frame[14:]
    if payload[:4] != MAGIC:
        raise VerifyError("payload_magic=MISMATCH")
    run_id = payload[4:8]
    sequence = int.from_bytes(payload[8:16], "big")
    payload_len = int.from_bytes(payload[16:18], "big")
    digest = payload[18:50]
    if payload_len != DIGEST_LEN:
        raise VerifyError(f"payload_len_field={payload_len}_EXPECTED_{DIGEST_LEN}")
    expected_digest = hashlib.sha256(payload[:18]).digest()
    if digest != expected_digest:
        raise VerifyError("payload_digest=MISMATCH")
    return {
        "source_mac": frame[6:12].hex(),
        "destination_mac": frame[:6].hex(),
        "ethertype": f"{ethertype:04x}",
        "run_id": run_id.hex(),
        "sequence": sequence,
        "payload_len": payload_len,
        "digest": digest.hex(),
        "frame_len": len(frame),
    }


def verify(data, expected_run_id, expected_sequence, expected_source):
    precision, packets = parse_pcap(data)
    matches = []
    for index, ts_sec, ts_frac, frame, incl_len, orig_len in packets:
        if len(frame) >= 14 and int.from_bytes(frame[12:14], "big") == ETHERTYPE:
            if incl_len != orig_len:
                raise VerifyError(f"matching_packet_{index}=CAPTURE_TRUNCATED")
            details = inspect_frame(frame)
            details.update({
                "packet_index": index,
                "timestamp_seconds": ts_sec,
                "timestamp_fraction": ts_frac,
                "timestamp_precision": precision,
            })
            matches.append(details)

    if len(matches) != 1:
        raise VerifyError(f"matching_frame_count={len(matches)}_EXPECTED_1")
    result = matches[0]
    if result["run_id"] != expected_run_id.lower():
        raise VerifyError("run_id=MISMATCH")
    if result["sequence"] != expected_sequence:
        raise VerifyError("sequence=MISMATCH")
    if expected_source and result["source_mac"] != expected_source.replace(":", "").lower():
        raise VerifyError("source_mac=MISMATCH")
    return result


def make_test_pcap():
    run_id = bytes.fromhex("01020304")
    sequence = 1
    payload = MAGIC + run_id + sequence.to_bytes(8, "big") + DIGEST_LEN.to_bytes(2, "big")
    payload += hashlib.sha256(payload).digest()
    frame = b"\xff" * 6 + bytes.fromhex("020000000001") + ETHERTYPE.to_bytes(2, "big") + payload
    global_header = b"\xd4\xc3\xb2\xa1" + struct.pack("<HHIIII", 2, 4, 0, 0, 65535, 1)
    record = struct.pack("<IIII", 1700000000, 123456, len(frame), len(frame)) + frame
    return global_header + record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pcap", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--sequence", type=lambda value: int(value, 0))
    parser.add_argument("--source-mac")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        try:
            result = verify(make_test_pcap(), "01020304", 1, "02:00:00:00:00:01")
            assert result["frame_len"] == FRAME_LEN
            print("pcap_parser_test=PASS")
            print("frame_validation_test=PASS")
            print("self_test=PASS")
            return 0
        except (VerifyError, AssertionError) as exc:
            print(f"self_test=FAIL reason={exc}", file=sys.stderr)
            return 1

    if args.pcap is None or args.run_id is None or args.sequence is None:
        parser.error("--pcap, --run-id and --sequence are required unless --self-test is used")
    if len(args.run_id) != 8:
        parser.error("--run-id must be exactly 8 hexadecimal characters")
    try:
        bytes.fromhex(args.run_id)
        result = verify(args.pcap.read_bytes(), args.run_id, args.sequence, args.source_mac)
    except (OSError, ValueError, VerifyError) as exc:
        print(f"pcap_verification=FAIL reason={exc}", file=sys.stderr)
        return 1

    print("pcap_verification=PASS")
    for key, value in result.items():
        print(f"{key}={value}")
    print("line_delivery=ONE_MATCHING_FRAME_CAPTURED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

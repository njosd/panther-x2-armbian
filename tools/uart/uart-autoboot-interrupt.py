#!/usr/bin/env python3
"""Automatically interrupt Panther X2 U-Boot autoboot over UART.

Reconstructed from the verified 2026-11-18 execution record. This is not
claimed to be a byte-for-byte recovery of the original terminal heredoc.
It only reads UART output and transmits Ctrl+C; it contains no storage commands.
"""

import re
import sys
import time

import serial

PORT = "/dev/cu.usbserial-1460"
BAUD = 1500000
DURATION = 20.0
INTERVAL = 0.05
POST_DETECT_READ = 2.0
PROMPT_RE = re.compile(rb"(?m)(=>|U-Boot>)\\s*$")


def main() -> int:
    ser = None
    output = bytearray()
    sent = 0
    detected_at = None
    started = time.monotonic()

    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0.05,
            write_timeout=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        print(f"Listening on {PORT} at {BAUD} baud (8N1).", flush=True)
        next_send = time.monotonic()

        while True:
            now = time.monotonic()
            waiting_for_prompt = detected_at is None

            if waiting_for_prompt and now - started >= DURATION:
                print("Timed out waiting for U-Boot prompt.", flush=True)
                break

            if waiting_for_prompt and now >= next_send:
                ser.write(b"\\x03")
                ser.flush()
                sent += 1
                next_send = now + INTERVAL

            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                output.extend(chunk)
                if len(output) > 4096:
                    del output[:-4096]
                sys.stdout.write(chunk.decode("utf-8", errors="replace"))
                sys.stdout.flush()

                if detected_at is None and PROMPT_RE.search(output):
                    detected_at = time.monotonic()
                    print("\\nU-Boot prompt detected. Stopping Ctrl+C.", flush=True)

            if detected_at is not None and time.monotonic() - detected_at >= POST_DETECT_READ:
                break

        print(f"Ctrl+C sent: {sent} times", flush=True)
        return 0 if detected_at is not None else 1

    except Exception as exc:
        print(f"UART error: {exc}", file=sys.stderr, flush=True)
        return 2
    finally:
        if ser is not None and ser.is_open:
            ser.close()
            print("Serial port closed.", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())

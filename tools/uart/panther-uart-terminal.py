#!/usr/bin/env python3
"""Reliable interactive macOS UART terminal for Panther X2.

Transparent bidirectional serial terminal. The Mac terminal is put in raw
mode (local echo/canonical buffering disabled); Ctrl+C is passed to the target.
Use Ctrl+] followed by . to exit locally.
"""

from __future__ import annotations

import argparse
import os
import select
import termios
import tty
from pathlib import Path

import serial

DEFAULT_PORT = "/dev/cu.usbserial-1460"
DEFAULT_BAUD = 1500000
BRACKETED_PASTE_OFF = b"\x1b[?2004l"
BRACKETED_PASTE_ON = b"\x1b[?2004h"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=DEFAULT_PORT, help="macOS serial device")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument(
        "--log-prefix",
        default=str(Path.home() / "panther-uart-session"),
        help="prefix for separate .rx.bin and .tx.bin logs (default: ~/panther-uart-session)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tty_fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    old_tty = termios.tcgetattr(tty_fd)
    ser = None
    rx_log = tx_log = None
    pending_escape = False
    exit_requested = False
    rx_path = Path(args.log_prefix + ".rx.bin")
    tx_path = Path(args.log_prefix + ".tx.bin")

    try:
        tty.setraw(tty_fd, when=termios.TCSANOW)
        # Prevent terminal-emulator bracketed-paste wrappers from reaching U-Boot.
        os.write(tty_fd, BRACKETED_PASTE_OFF)
        ser = serial.Serial(
            port=args.port,
            baudrate=args.baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0,
            write_timeout=2,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        rx_log = open(rx_path, "ab", buffering=0)
        tx_log = open(tx_path, "ab", buffering=0)

        banner = (
            f"\r\nUART {args.port} | {args.baud} 8N1 | local echo OFF | raw mode\r\n"
            f"RX log: {rx_path}\r\nTX log: {tx_path}\r\n"
            "Exit locally: Ctrl+] then .   (Ctrl+C is sent to Panther X2)\r\n\r\n"
        )
        os.write(tty_fd, banner.encode())

        while not exit_requested:
            readable, _, _ = select.select([tty_fd, ser.fileno()], [], [], 0.25)
            if ser.fileno() in readable:
                data = ser.read(ser.in_waiting or 1)
                if data:
                    rx_log.write(data)
                    os.write(tty_fd, data)

            if tty_fd in readable:
                data = os.read(tty_fd, 4096)
                if not data:
                    break
                out = bytearray()
                for byte in data:
                    if pending_escape:
                        pending_escape = False
                        if byte == ord("."):
                            exit_requested = True
                            break
                        out.extend((0x1D, byte))
                    elif byte == 0x1D:
                        pending_escape = True
                    else:
                        out.append(byte)
                if out:
                    ser.write(out)
                    tx_log.write(out)

        if pending_escape:
            ser.write(b"\x1d")
            tx_log.write(b"\x1d")
        return 0

    except Exception as exc:
        try:
            os.write(tty_fd, f"\r\nUART terminal error: {exc}\r\n".encode())
        except Exception:
            pass
        return 1
    finally:
        if ser is not None and ser.is_open:
            ser.close()
        if rx_log is not None:
            rx_log.close()
        if tx_log is not None:
            tx_log.close()
        try:
            os.write(tty_fd, BRACKETED_PASTE_ON)
            termios.tcsetattr(tty_fd, termios.TCSANOW, old_tty)
            os.write(tty_fd, b"\r\nUART terminal closed; local terminal settings restored.\r\n")
        finally:
            os.close(tty_fd)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Interactive macOS UART terminal for Panther X2.

The Mac terminal is put in raw mode (local echo/canonical buffering disabled).
Keyboard bytes are forwarded to UART after removing terminal bracketed-paste
wrappers. UART RX bytes are displayed. Ctrl+C is passed to the target.
Press Ctrl+] (one key chord) to exit locally.
"""

from __future__ import annotations

import argparse
import os
import select
import termios
import time
import tty
from pathlib import Path

import serial

DEFAULT_PORT = "/dev/cu.usbserial-1460"
DEFAULT_BAUD = 1500000
BRACKETED_PASTE_OFF = b"\x1b[?2004l"
BRACKETED_PASTE_ON = b"\x1b[?2004h"
PASTE_START = b"\x1b[200~"
PASTE_END = b"\x1b[201~"
PASTE_MARKERS = (PASTE_START, PASTE_END)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=DEFAULT_PORT, help="macOS serial device")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument(
        "--log-prefix",
        default=str(Path.home() / "panther-uart-session"),
        help="log filename prefix (a unique timestamp and PID are added)",
    )
    return parser.parse_args()


def write_terminal(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def strip_paste_markers(data: bytes, pending: bytearray) -> bytes:
    """Remove bracketed-paste delimiters, including when split across reads."""
    pending.extend(data)
    output = bytearray()
    while pending:
        if any(pending.startswith(marker) for marker in PASTE_MARKERS):
            marker = next(marker for marker in PASTE_MARKERS if pending.startswith(marker))
            del pending[: len(marker)]
            continue
        if any(marker.startswith(pending) for marker in PASTE_MARKERS):
            break
        output.append(pending[0])
        del pending[0]
    return bytes(output)


def main() -> int:
    args = parse_args()
    tty_fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY)
    old_tty = None
    ser = None
    rx_log = None
    tx_log = None
    raw_enabled = False
    result = 0
    paste_pending = bytearray()

    stamp = time.strftime("%Y%m%d-%H%M%S")
    log_base = f"{args.log_prefix}-{stamp}-{os.getpid()}"
    rx_path = Path(log_base + ".rx.bin")
    tx_path = Path(log_base + ".tx.bin")

    try:
        old_tty = termios.tcgetattr(tty_fd)
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
        rx_log = open(rx_path, "xb", buffering=0)
        tx_log = open(tx_path, "xb", buffering=0)

        tty.setraw(tty_fd, when=termios.TCSANOW)
        raw_enabled = True
        write_terminal(tty_fd, BRACKETED_PASTE_OFF)

        banner = (
            f"\r\nUART {args.port} | {args.baud} 8N1 | local echo OFF | raw mode\r\n"
            f"RX log: {rx_path}\r\nTX log: {tx_path}\r\n"
            "Local exit: press Ctrl+] once. Ctrl+C is sent to Panther X2.\r\n\r\n"
        )
        write_terminal(tty_fd, banner.encode())

        exit_requested = False
        while not exit_requested:
            readable, _, _ = select.select([tty_fd], [], [], 0.02)

            if readable:
                data = os.read(tty_fd, 4096)
                if not data:
                    break

                filtered = strip_paste_markers(data, paste_pending)
                outgoing = bytearray()
                for byte in filtered:
                    if byte == 0x1D:
                        exit_requested = True
                        break
                    outgoing.append(byte)

                if outgoing:
                    ser.write(outgoing)
                    tx_log.write(outgoing)

            waiting = ser.in_waiting
            if waiting:
                incoming = ser.read(waiting)
                if incoming:
                    rx_log.write(incoming)
                    write_terminal(tty_fd, incoming)

        if paste_pending:
            pending_bytes = bytes(paste_pending)
            ser.write(pending_bytes)
            tx_log.write(pending_bytes)

    except Exception as exc:
        result = 1
        try:
            if raw_enabled:
                write_terminal(tty_fd, f"\r\nUART terminal error: {exc}\r\n".encode())
            else:
                print(f"UART terminal error: {exc}")
        except Exception:
            pass
    finally:
        if ser is not None and ser.is_open:
            ser.close()
        if rx_log is not None:
            rx_log.close()
        if tx_log is not None:
            tx_log.close()

        if old_tty is not None:
            try:
                if raw_enabled:
                    write_terminal(tty_fd, BRACKETED_PASTE_ON)
                termios.tcsetattr(tty_fd, termios.TCSANOW, old_tty)
                if raw_enabled:
                    write_terminal(
                        tty_fd,
                        b"\r\nUART terminal closed; local terminal settings restored.\r\n",
                    )
            except Exception:
                pass
        os.close(tty_fd)

    return result


if __name__ == "__main__":
    raise SystemExit(main())

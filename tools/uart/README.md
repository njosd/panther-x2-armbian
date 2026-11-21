# Panther X2 UART autoboot interruption helper

This script automates the previously real-device-tested U-Boot autoboot interruption method: it listens to UART, repeatedly transmits Ctrl+C (`0x03`) during the autoboot window, detects the U-Boot command prompt, then stops transmitting and reads for two more seconds.

## Provenance and fidelity

The 2026-11-18 execution records establish the operational parameters and observed behavior. The complete original terminal heredoc could not be retrieved byte-for-byte from the available conversation archive. Therefore `uart-autoboot-interrupt.py` is a carefully reconstructed, syntax-checked archival implementation matching the recovered later-run parameters; it is **not represented as the exact original source** and has not itself been re-run against the hardware.

Recovered later-run parameters:

- Python environment: `$HOME/panther-uart-venv`
- Serial device at the time: `/dev/cu.usbserial-1460`
- 1500000 baud, 8N1
- pySerial, `timeout=0.05`, `write_timeout=1`
- software/hardware flow control disabled (`xonxoff`, `rtscts`, `dsrdtr`)
- Ctrl+C byte `0x03` every 50 ms, up to 20 seconds
- rolling UART capture buffer of 4096 bytes
- prompt pattern `(?m)(=>|U-Boot>)\\s*$`
- continue reading for two seconds after prompt detection, then close serial in `finally`

A previous run used `timeout=0.02`, `write_timeout=1`, a 2000-character rolling buffer, and prompt pattern `(?m)^\\s*(=>|U-Boot>)\\s*$`. Historical runs reported 160 and 73 Ctrl+C transmissions respectively before detecting the prompt.

## Run

First verify the serial device path on the current Mac; it is machine/adapter-specific. Then:

```sh
"$HOME/panther-uart-venv/bin/python" /path/to/uart-autoboot-interrupt.py
```

The script only reads UART output and sends Ctrl+C. It does not issue U-Boot commands and contains no MMC, flash, environment-save, upgrade, or storage-write operations. It does not alter the eMMC or TF. After the prompt appears, the operator takes over manually.

Do not assume this prompt/timing behavior on JP-TvBox or other U-Boot builds without separate verification.

## Interactive UART terminal (separate from autoboot helper)

`panther-uart-terminal.py` is the interactive bidirectional terminal. It is deliberately separate from `uart-autoboot-interrupt.py`, which only interrupts autoboot and then exits.

The first interactive-terminal implementation was tested on the user's iMac on 2026-11-21 and failed acceptance: the TX log contained duplicated/mangled command bytes and the intended two-key local exit did not reliably work. The script has since been revised; the revision is **not yet hardware-validated**.

Current revision design:

- Opens `/dev/tty` directly, not Python stdin.
- Uses POSIX raw mode to disable local echo, canonical buffering and terminal-generated Ctrl+C signals while connected.
- Forwards keyboard bytes to UART and displays only UART RX bytes.
- Disables bracketed-paste wrappers during the session.
- Ctrl+C is forwarded as byte `0x03` to the target.
- **Press Ctrl+] once to exit locally**; no second key is required. This is intentionally different from the failed first revision.
- Creates unique RX/TX log files for every session using a timestamp and process ID; it does not append to or overwrite earlier session logs.
- Restores the original terminal attributes and closes the serial port/logs in `finally`.

Run from an ordinary interactive Terminal window (not a Python heredoc):

```sh
"$HOME/panther-uart-venv/bin/python" "$HOME/path/to/panther-x2-armbian/tools/uart/panther-uart-terminal.py"
```

Optional overrides:

```sh
"$HOME/panther-uart-venv/bin/python" panther-uart-terminal.py --port /dev/cu.usbserial-1460 --baud 1500000 --log-prefix "$HOME/panther-uart-session"
```

**Validation status:** The user's iMac confirmed Python 3 compilation, pySerial 3.5 and the serial device node. The first revision connected and received Armbian shell output, but its TX log showed malformed/duplicated bytes and the exit sequence failed. The revised single-key-exit implementation has not yet been run on the user's iMac or connected to the hardware. Character integrity, Enter, paste, Ctrl+C forwarding, single-key exit and terminal restoration remain to be tested. The old `panther-uart.py` is not overwritten. The historical autoboot-interrupt script remains a separate tool.

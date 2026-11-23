#!/usr/bin/env python3
"""Derive a Panther X2 B1 DTB with all non-target I/O disabled."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def block_span(text: str, marker: str) -> tuple[int, int]:
    hits = [m.start() for m in re.finditer(re.escape(marker), text)]
    if len(hits) != 1:
        raise RuntimeError(f"expected exactly one marker {marker!r}, found {len(hits)}")
    marker_pos = hits[0]
    start = text.rfind("\n", 0, marker_pos) + 1
    brace = text.find("{", marker_pos)
    if brace < 0:
        raise RuntimeError(f"opening brace not found for {marker!r}")

    depth = 0
    state = "normal"
    i = brace
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "line":
            if ch == "\n":
                state = "normal"
            i += 1
        elif state == "block":
            if ch == "*" and nxt == "/":
                state = "normal"
                i += 2
            else:
                i += 1
        elif state == "string":
            if ch == "\\":
                i += 2
            elif ch == '"':
                state = "normal"
                i += 1
            else:
                i += 1
        elif ch == "/" and nxt == "/":
            state = "line"
            i += 2
        elif ch == "/" and nxt == "*":
            state = "block"
            i += 2
        elif ch == '"':
            state = "string"
            i += 1
        elif ch == "{":
            depth += 1
            i += 1
        elif ch == "}":
            depth -= 1
            i += 1
            if depth == 0:
                end = i
                while end < len(text) and text[end] in " \t\r\n":
                    end += 1
                if end < len(text) and text[end] == ";":
                    end += 1
                else:
                    raise RuntimeError(f"block terminator missing for {marker!r}")
                return start, end
        else:
            i += 1
    raise RuntimeError(f"unclosed block for {marker!r}")


def remove_block(text: str, marker: str) -> str:
    start, end = block_span(text, marker)
    return text[:start] + text[end:]


def replace_block(text: str, marker: str, replacement: str) -> str:
    start, end = block_span(text, marker)
    marker_pos = text.find(marker, start)
    indent = text[start:marker_pos]
    rendered = indent + replacement.replace("\n", "\n" + indent)
    return text[:start] + rendered + text[end:]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: prepare-clean-dtb.py <rk3566-panther-x2.dts>")
    path = Path(sys.argv[1])
    original = path.read_text()
    if 'model = "Panther X2";' not in original or '"panther,x2"' not in original:
        raise SystemExit("refusing to patch a DTS that is not the Panther X2 board file")

    text = original

    # Remove board-specific Wi-Fi/BT support descriptions, GPIOs and LEDs.
    remove_markers = (
        "gmac1_clkin: external-gmac1-clock",
        "sdio_pwrseq: sdio-pwrseq",
        "sdio-pwrseq {",
        "wireless-wlan {",
        "\tbt {",
        "led_wifi: led-wifi",
        "led_eth: led-eth",
        "led_wifi_enable_h: led-wifi-enable-h",
        "led_eth_enable_h: led-eth-enable-h",
    )
    for marker in remove_markers:
        text = remove_block(text, marker)

    # Linux B1 is RAM-only. TF is read by U-Boot before Linux starts.
    # Keep UART2 (ttyS02) enabled for the only console.
    disabled = (
        ("&gmac1 {", '&gmac1 {\n\tstatus = "disabled";\n};'),
        ("&mdio1 {", '&mdio1 {\n\tstatus = "disabled";\n};'),
        ("&sdhci {", '&sdhci {\n\tstatus = "disabled";\n};'),
        ("&sdmmc0 {", '&sdmmc0 {\n\tstatus = "disabled";\n};'),
        ("&sdmmc1 {", '&sdmmc1 {\n\tstatus = "disabled";\n};'),
        ("&uart1 {", '&uart1 {\n\tstatus = "disabled";\n};'),
        ("&usb_host0_xhci {", '&usb_host0_xhci {\n\tstatus = "disabled";\n};'),
        ("&usb_host0_ohci {", '&usb_host0_ohci {\n\tstatus = "disabled";\n};'),
        ("&usb_host0_ehci {", '&usb_host0_ehci {\n\tstatus = "disabled";\n};'),
        ("&usb2phy0 {", '&usb2phy0 {\n\tstatus = "disabled";\n};'),
        ("&usb2phy0_host {", '&usb2phy0_host {\n\tstatus = "disabled";\n};'),
        ("&usb2phy0_otg {", '&usb2phy0_otg {\n\tstatus = "disabled";\n};'),
    )
    for marker, replacement in disabled:
        text = replace_block(text, marker, replacement)

    # Keep the UART2 alias required by /chosen/stdout-path. The inherited
    # rk356x-base.dtsi aliases node also defines serial2 = &uart2; replacing
    # the whole node without this entry silently breaks earlycon resolution.
    # MMC/Ethernet aliases are not needed by the RAM-only B1 kernel.
    text = replace_block(
        text,
        "aliases {",
        "aliases {\n\tserial2 = &uart2;\n};",
    )

    forbidden_residue = re.compile(
        r"\b(?:wifi|wireless|bluetooth|bt_enable_h|bt_host_wake_l|bt_wake_l|"
        r"sdio_pwrseq|gmac1_clkin|ethernet-phy|ethernet0|mmc0|mmc1|mmc2)\b",
        re.IGNORECASE,
    )
    if forbidden_residue.search(text):
        raise SystemExit("Wi-Fi/BT/MMC/Ethernet residue remains in derived board DTS")

    for marker in (
        "&gmac1 {", "&mdio1 {", "&sdhci {", "&sdmmc0 {", "&sdmmc1 {",
        "&uart1 {", "&usb_host0_xhci {", "&usb_host0_ohci {", "&usb_host0_ehci {",
        "&usb2phy0 {", "&usb2phy0_host {", "&usb2phy0_otg {",
    ):
        start, end = block_span(text, marker)
        if not re.search(r'status\s*=\s*"disabled"', text[start:end]):
            raise SystemExit(f"{marker} is not explicitly disabled")

    path.write_text(text)
    print(f"Prepared B1 clean-test DTB source: {path}")
    print("Disabled: GMAC/MDIO/PHY, eMMC/TF/SDIO, Bluetooth UART, USB host/PHY")
    print("Removed: Wi-Fi/BT GPIO/power-sequence nodes, Wi-Fi/Ethernet LEDs, MMC/Ethernet aliases")
    print("Retained: serial2 alias -> UART2 for earlycon")


if __name__ == "__main__":
    main()

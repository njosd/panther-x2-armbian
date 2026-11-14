#!/usr/bin/env python3
"""Fail-closed semantic comparison of Panther X2 NPU DTB candidates.

Device Tree Compiler may renumber phandles when a candidate begins referencing
previously unreferenced nodes. Compare reference targets by node path rather
than raw phandle numbers, while preserving argument cells and all other data.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REFERENCE_PROPERTIES = {
    "clocks", "assigned-clocks", "assigned-clock-parents", "resets",
    "power-domains", "iommus", "interrupt-parent", "interrupts-extended",
    "operating-points-v2", "memory-region", "phys", "dmas", "dma-names",
    "mboxes", "pwms", "io-channels", "io-channel-names", "nvmem-cells",
    "cpu", "cpu-supply", "rockchip,grf", "rockchip,pmu",
}
PHANDLE_PROPERTIES = {"phandle", "linux,phandle"}


def run_fdtget(dtb: Path, *args: str, required: bool = True) -> str:
    proc = subprocess.run(
        ["fdtget", str(dtb), *args], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if proc.returncode:
        if required:
            raise RuntimeError(
                f"fdtget failed ({' '.join(args)}): {proc.stderr.strip()}"
            )
        return ""
    return proc.stdout.strip()


def walk_nodes(dtb: Path, node: str = "/") -> list[str]:
    children = run_fdtget(dtb, "-l", node, required=False).split()
    found = [node]
    for child in children:
        path = ("/" + child) if node == "/" else (node.rstrip("/") + "/" + child)
        found.extend(walk_nodes(dtb, path))
    return found


def property_names(dtb: Path, node: str) -> list[str]:
    return run_fdtget(dtb, "-p", node, required=False).split()


def phandle_map(dtb: Path) -> dict[int, str]:
    result: dict[int, str] = {}
    for node in walk_nodes(dtb):
        raw = run_fdtget(dtb, "-t", "x", node, "phandle", required=False)
        if not raw:
            raw = run_fdtget(dtb, "-t", "x", node, "linux,phandle", required=False)
        if raw:
            value = int(raw.split()[0], 16)
            if value in result:
                raise RuntimeError(
                    f"Duplicate phandle 0x{value:x}: {result[value]} and {node}"
                )
            result[value] = node
    return result


def is_reference_property(name: str) -> bool:
    return (
        name in REFERENCE_PROPERTIES
        or name.endswith("-supply")
        or name.endswith("-gpios")
        or name.startswith("pinctrl-")
        or name.endswith("-parent") and name != "interrupt-parent"
    )


def normalized_property(dtb: Path, node: str, name: str,
                        handles: dict[int, str]) -> str | None:
    if name in PHANDLE_PROPERTIES:
        # The numeric handle itself is an implementation detail, not semantics.
        return None
    if is_reference_property(name):
        raw = run_fdtget(dtb, "-t", "x", node, name, required=False)
        cells = []
        for token in raw.split():
            value = int(token, 16)
            target = handles.get(value)
            cells.append(f"@{target}" if target else f"0x{value:x}")
        return " ".join(cells)
    return run_fdtget(dtb, node, name, required=False)


def node_props(dtb: Path, node: str,
               handles: dict[int, str]) -> dict[str, str]:
    result = {}
    for name in property_names(dtb, node):
        value = normalized_property(dtb, node, name, handles)
        if value is not None:
            result[name] = value
    return result


def prop(dtb: Path, node: str, name: str,
         handles: dict[int, str] | None = None) -> str:
    return normalized_property(dtb, node, name, handles or phandle_map(dtb)) or ""


def regulator_path(dtb: Path, regulator_name: str) -> str:
    matches = [
        node for node in walk_nodes(dtb)
        if run_fdtget(dtb, node, "regulator-name", required=False) == regulator_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one regulator-name={regulator_name}, found {matches}"
        )
    return matches[0]


def assert_supply_target(dtb: Path, consumer: str, supply_prop: str,
                         regulator_name: str) -> None:
    target = regulator_path(dtb, regulator_name)
    handles = phandle_map(dtb)
    actual = run_fdtget(dtb, "-t", "x", consumer, supply_prop).split()
    if len(actual) != 1:
        raise RuntimeError(f"{consumer}:{supply_prop} must contain exactly one phandle")
    resolved = handles.get(int(actual[0], 16))
    if resolved != target:
        raise RuntimeError(
            f"{consumer}:{supply_prop} resolves to {resolved}, "
            f"not {regulator_name} at {target}"
        )


def compare_trees(base: Path, candidate: Path, allowed: dict[str, set[str]],
                  label: str) -> list[str]:
    base_nodes = set(walk_nodes(base))
    cand_nodes = set(walk_nodes(candidate))
    if base_nodes != cand_nodes:
        raise RuntimeError(
            f"{label}: node tree changed; added={sorted(cand_nodes-base_nodes)}, "
            f"missing={sorted(base_nodes-cand_nodes)}"
        )

    base_handles = phandle_map(base)
    cand_handles = phandle_map(candidate)
    changes: list[str] = []
    for node in sorted(base_nodes):
        old = node_props(base, node, base_handles)
        new = node_props(candidate, node, cand_handles)
        for name in sorted(set(old) | set(new)):
            if old.get(name) == new.get(name):
                continue
            if name in allowed.get(node, set()):
                changes.append(
                    f"{node}:{name}: {old.get(name)!r} -> {new.get(name)!r}"
                )
            else:
                raise RuntimeError(
                    f"{label}: unexpected semantic property change at "
                    f"{node}:{name}: {old.get(name)!r} -> {new.get(name)!r}"
                )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--vendor-candidate", required=True, type=Path)
    parser.add_argument("--irqname-candidate", required=True, type=Path)
    args = parser.parse_args()

    bus, npu, mmu = "/bus-npu", "/npu@fde40000", "/iommu@fde4b000"
    allowed = {
        bus: {"bus-supply", "pvtm-supply", "status"},
        npu: {"rknpu-supply", "status"},
        mmu: {"status"},
    }
    vendor_changes = compare_trees(
        args.baseline, args.vendor_candidate, allowed, "vendor-equivalent candidate"
    )
    irq_allowed = {**allowed, npu: allowed[npu] | {"interrupt-names"}}
    irq_changes = compare_trees(
        args.baseline, args.irqname_candidate, irq_allowed, "IRQ-name candidate"
    )
    extension_changes = compare_trees(
        args.vendor_candidate, args.irqname_candidate,
        {npu: {"interrupt-names"}}, "IRQ-name-only delta",
    )

    for candidate, label in (
        (args.vendor_candidate, "vendor-equivalent"),
        (args.irqname_candidate, "IRQ-name"),
    ):
        handles = phandle_map(candidate)
        for node in (bus, npu, mmu):
            if prop(candidate, node, "status", handles) != "okay":
                raise RuntimeError(f"{label}: {node} is not status=okay")
        assert_supply_target(candidate, bus, "bus-supply", "vdd_logic")
        assert_supply_target(candidate, bus, "pvtm-supply", "vdd_cpu")
        assert_supply_target(candidate, npu, "rknpu-supply", "vdd_npu")

        for name in (
            "interrupts", "clocks", "resets", "power-domains",
            "operating-points-v2", "iommus",
        ):
            if prop(candidate, npu, name, handles) != prop(args.baseline, npu, name):
                raise RuntimeError(f"{label}: NPU {name} target/specifier differs from baseline")
        for name in ("clocks", "operating-points-v2"):
            if prop(candidate, bus, name, handles) != prop(args.baseline, bus, name):
                raise RuntimeError(f"{label}: bus_npu {name} differs from baseline")
        if prop(candidate, mmu, "interrupts", handles) != prop(args.baseline, mmu, "interrupts"):
            raise RuntimeError(f"{label}: IOMMU IRQ differs from baseline")

    irq_names = run_fdtget(args.irqname_candidate, npu, "interrupt-names")
    if irq_names != "npu_irq":
        raise RuntimeError(f"IRQ-name candidate has unexpected interrupt-names={irq_names!r}")
    if run_fdtget(args.vendor_candidate, npu, "interrupt-names", required=False):
        raise RuntimeError("Vendor-equivalent candidate unexpectedly adds interrupt-names")

    print("SEMANTIC_DTB_AUDIT=PASS")
    print("Phandle references normalized to target node paths before comparison.")
    print(f"Vendor-equivalent allowed changes: {len(vendor_changes)}")
    for item in vendor_changes:
        print(f"  {item}")
    print(f"IRQ-name candidate allowed changes: {len(irq_changes)}")
    for item in irq_changes:
        print(f"  {item}")
    print("IRQ-name-only delta:")
    for item in extension_changes:
        print(f"  {item}")
    print("Supply phandles resolve to vdd_logic, vdd_cpu and vdd_npu.")
    print("NPU IRQ/clocks/resets/power-domain/OPP/IOMMU and bus clocks/OPP targets preserved.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise SystemExit(1)

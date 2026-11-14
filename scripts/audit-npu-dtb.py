#!/usr/bin/env python3
"""Semantic comparison for CI-only Panther X2 RK3566 NPU DTB candidates.

Uses the device-tree-compiler fdtget utility. It intentionally fails closed:
any DTB tree/property difference outside the explicit Panther NPU board fragment
allowlist is reported as an unexpected change.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def fdtget(dtb: Path, *args: str, required: bool = True) -> str:
    proc = subprocess.run(
        ["fdtget", str(dtb), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode:
        if required:
            raise RuntimeError(
                f"fdtget failed ({' '.join(args)}): {proc.stderr.strip()}"
            )
        return ""
    return proc.stdout.strip()


def walk_nodes(dtb: Path, node: str = "/") -> list[str]:
    children = fdtget(dtb, "-l", node, required=False).split()
    found = [node]
    for child in children:
        path = ("/" + child) if node == "/" else (node.rstrip("/") + "/" + child)
        found.extend(walk_nodes(dtb, path))
    return found


def node_props(dtb: Path, node: str) -> dict[str, str]:
    names = fdtget(dtb, "-p", node, required=False).split()
    return {name: fdtget(dtb, node, name, required=False) for name in names}


def prop(dtb: Path, node: str, name: str) -> str:
    return fdtget(dtb, node, name)


def phandle(dtb: Path, node: str) -> int:
    raw = fdtget(dtb, "-t", "x", node, "phandle", required=False)
    if not raw:
        raw = fdtget(dtb, "-t", "x", node, "linux,phandle")
    return int(raw.split()[0], 16)


def regulator_path(dtb: Path, regulator_name: str) -> str:
    matches = []
    for node in walk_nodes(dtb):
        if fdtget(dtb, node, "regulator-name", required=False) == regulator_name:
            matches.append(node)
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one regulator-name={regulator_name}, found {matches}"
        )
    return matches[0]


def assert_supply_target(dtb: Path, consumer: str, supply_prop: str,
                         regulator_name: str) -> None:
    target = regulator_path(dtb, regulator_name)
    actual = int(fdtget(dtb, "-t", "x", consumer, supply_prop).split()[0], 16)
    expected = phandle(dtb, target)
    if actual != expected:
        raise RuntimeError(
            f"{consumer}:{supply_prop} points to phandle 0x{actual:x}, "
            f"not {regulator_name} at {target} (0x{expected:x})"
        )


def compare_trees(base: Path, candidate: Path, allowed: dict[str, set[str]],
                  label: str) -> list[str]:
    base_nodes = set(walk_nodes(base))
    cand_nodes = set(walk_nodes(candidate))
    if base_nodes != cand_nodes:
        missing = sorted(base_nodes - cand_nodes)
        added = sorted(cand_nodes - base_nodes)
        raise RuntimeError(
            f"{label}: node tree changed; added={added}, missing={missing}"
        )

    changes: list[str] = []
    for node in sorted(base_nodes):
        old = node_props(base, node)
        new = node_props(candidate, node)
        for name in sorted(set(old) | set(new)):
            if old.get(name) == new.get(name):
                continue
            if name in allowed.get(node, set()):
                changes.append(f"{node}:{name}: {old.get(name)!r} -> {new.get(name)!r}")
            else:
                raise RuntimeError(
                    f"{label}: unexpected property change at {node}:{name}: "
                    f"{old.get(name)!r} -> {new.get(name)!r}"
                )
    return changes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--vendor-candidate", required=True, type=Path)
    parser.add_argument("--irqname-candidate", required=True, type=Path)
    args = parser.parse_args()

    bus = "/bus-npu"
    npu = "/npu@fde40000"
    mmu = "/iommu@fde4b000"
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
        args.vendor_candidate,
        args.irqname_candidate,
        {npu: {"interrupt-names"}},
        "IRQ-name-only delta",
    )

    for candidate, label in (
        (args.vendor_candidate, "vendor-equivalent"),
        (args.irqname_candidate, "IRQ-name"),
    ):
        for node in (bus, npu, mmu):
            if prop(candidate, node, "status") != "okay":
                raise RuntimeError(f"{label}: {node} is not status=okay")

        assert_supply_target(candidate, bus, "bus-supply", "vdd_logic")
        assert_supply_target(candidate, bus, "pvtm-supply", "vdd_cpu")
        assert_supply_target(candidate, npu, "rknpu-supply", "vdd_npu")

        # Board fragments must not silently replace the SoC's resource topology.
        for name in (
            "interrupts", "clocks", "resets", "power-domains",
            "operating-points-v2", "iommus",
        ):
            if prop(candidate, npu, name) != prop(args.baseline, npu, name):
                raise RuntimeError(f"{label}: NPU {name} differs from SoC baseline")
        for name in ("clocks", "operating-points-v2"):
            if prop(candidate, bus, name) != prop(args.baseline, bus, name):
                raise RuntimeError(f"{label}: bus_npu {name} differs from SoC baseline")
        if prop(candidate, mmu, "interrupts") != prop(args.baseline, mmu, "interrupts"):
            raise RuntimeError(f"{label}: IOMMU IRQ differs from SoC baseline")

    irq_names = fdtget(args.irqname_candidate, npu, "interrupt-names")
    if irq_names != "npu_irq":
        raise RuntimeError(f"IRQ-name candidate has unexpected interrupt-names={irq_names!r}")
    if fdtget(args.vendor_candidate, npu, "interrupt-names", required=False):
        raise RuntimeError("Vendor-equivalent candidate unexpectedly adds interrupt-names")

    print("SEMANTIC_DTB_AUDIT=PASS")
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
    print("NPU IRQ/clocks/resets/power-domain/OPP/IOMMU and bus clocks/OPP preserved.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"::error::{exc}", file=sys.stderr)
        raise SystemExit(1)

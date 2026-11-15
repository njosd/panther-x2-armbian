#!/usr/bin/env python3
"""Unit tests for DTB semantic reference normalization."""
from pathlib import Path
import importlib.util
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit-npu-dtb.py"
SPEC = importlib.util.spec_from_file_location("audit_npu_dtb", SCRIPT)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class ReferenceClassificationTests(unittest.TestCase):
    def test_reference_property_classes(self):
        for name in ("clocks", "resets", "power-domains", "iommus",
                     "interrupts-extended", "nvmem-cells", "memory-region",
                     "devfreq-events", "interrupt-parent", "rockchip,hw",
                     "ddr3_params", "vdd-supply", "pinctrl-0", "reset-gpios"):
            with self.subTest(name=name):
                self.assertTrue(audit.is_reference_property(name))
        for name in ("pinctrl-names", "clock-frequency", "reg", "status",
                     "compatible", "rockchip,grf-name"):
            with self.subTest(name=name):
                self.assertFalse(audit.is_reference_property(name))

    def test_symbols_node_values_are_strings_even_for_phandle_named_symbols(self):
        with patch.object(audit, "run_fdtget", return_value="/ddr3-params") as mocked:
            self.assertEqual(
                audit.normalized_property(
                    Path("tree.dtb"), "/__symbols__", "ddr3_params",
                    {0x10: "/provider-a", 0x11: "/provider-b"}
                ),
                "/ddr3-params",
            )
            mocked.assert_called_once_with(
                Path("tree.dtb"), "/__symbols__", "ddr3_params", required=False
            )

    def test_phandle_metadata_is_omitted(self):
        self.assertIsNone(
            audit.normalized_property(Path("tree.dtb"), "/node", "phandle", {})
        )
        self.assertIsNone(
            audit.normalized_property(Path("tree.dtb"), "/node", "linux,phandle", {})
        )


class NormalizationTests(unittest.TestCase):
    dtb = Path("tree.dtb")
    handles = {0x10: "/provider-a", 0x11: "/provider-b"}

    def test_direct_phandle_lists(self):
        for name in ("nvmem-cells", "memory-region", "devfreq-events",
                     "pinctrl-0"):
            with self.subTest(name=name), patch.object(
                audit, "run_fdtget", return_value="10 11"
            ):
                self.assertEqual(
                    audit.normalized_property(self.dtb, "/consumer", name, self.handles),
                    "@/provider-a @/provider-b",
                )

    def test_single_phandle(self):
        for name in ("rockchip,hw", "remote-endpoint", "phy-handle",
                     "snps,axi-config", "snps,mtl-rx-config", "snps,mtl-tx-config", "rockchip,srv"):
            with self.subTest(name=name), patch.object(
                audit, "run_fdtget", return_value="10"
            ):
                self.assertEqual(
                    audit.normalized_property(
                        self.dtb, "/consumer", name, self.handles
                    ),
                    "@/provider-a",
                )

    def test_provider_specifier_preserves_argument_cells(self):
        def fake_fdtget(_dtb, *args, required=True):
            if args[-1] == "clocks":
                return "10 3 11 4"
            if args[-1] == "#clock-cells":
                return "1"
            return ""

        with patch.object(audit, "run_fdtget", side_effect=fake_fdtget):
            self.assertEqual(
                audit.normalized_property(self.dtb, "/consumer", "clocks", self.handles),
                "@/provider-a(0x3) @/provider-b(0x4)",
            )

    def test_gpio_specifier_uses_gpio_cells(self):
        def fake_fdtget(_dtb, *args, required=True):
            if args[-1] == "reset-gpios":
                return "10 7 1"
            if args[-1] == "#gpio-cells":
                return "2"
            return ""

        with patch.object(audit, "run_fdtget", side_effect=fake_fdtget):
            self.assertEqual(
                audit.normalized_property(
                    self.dtb, "/consumer", "reset-gpios", self.handles
                ),
                "@/provider-a(0x7,0x1)",
            )

    def test_singular_gpio_property_uses_gpio_cells(self):
        def fake_fdtget(_dtb, *args, required=True):
            if args[-1] == "snps,reset-gpio":
                return "10 1 1"
            if args[-1] == "#gpio-cells":
                return "2"
            return ""

        with patch.object(audit, "run_fdtget", side_effect=fake_fdtget):
            self.assertEqual(
                audit.normalized_property(
                    self.dtb, "/ethernet", "snps,reset-gpio", self.handles
                ),
                "@/provider-a(0x1,0x1)",
            )

    def test_strings_and_integer_arrays_are_not_rewritten(self):
        with patch.object(audit, "run_fdtget", return_value="default") as mocked:
            self.assertEqual(
                audit.normalized_property(
                    self.dtb, "/consumer", "pinctrl-names", self.handles
                ),
                "default",
            )
            mocked.assert_called_once_with(
                self.dtb, "/consumer", "pinctrl-names", required=False
            )
        with patch.object(audit, "run_fdtget", return_value="10 11"):
            self.assertEqual(
                audit.normalized_property(
                    self.dtb, "/consumer", "vendor,numeric-table", self.handles
                ),
                "10 11",
            )

    def test_unknown_reference_fails_closed(self):
        with patch.object(audit, "run_fdtget", return_value="99"):
            with self.assertRaisesRegex(RuntimeError, "unknown phandle"):
                audit.normalized_property(
                    self.dtb, "/consumer", "memory-region", self.handles
                )

    def test_truncated_provider_specifier_fails_closed(self):
        def fake_fdtget(_dtb, *args, required=True):
            if args[-1] == "clocks":
                return "10"
            if args[-1] == "#clock-cells":
                return "1"
            return ""

        with patch.object(audit, "run_fdtget", side_effect=fake_fdtget):
            with self.assertRaisesRegex(RuntimeError, "truncated specifier"):
                audit.normalized_property(
                    self.dtb, "/consumer", "clocks", self.handles
                )


class FdtgetCommandTests(unittest.TestCase):
    def test_options_precede_dtb_path(self):
        with patch.object(audit.subprocess, "run") as mocked:
            mocked.return_value.returncode = 0
            mocked.return_value.stdout = "10"
            mocked.return_value.stderr = ""
            result = audit.run_fdtget(
                Path("tree.dtb"), "-t", "x", "/node", "clocks"
            )
        self.assertEqual(result, "10")
        self.assertEqual(
            mocked.call_args.args[0],
            ["fdtget", "-t", "x", "tree.dtb", "/node", "clocks"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

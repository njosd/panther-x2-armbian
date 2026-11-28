#!/bin/sh
# G4-P2 runtime collector.
# Read-only procfs/sysfs/debugfs observations only.
# No sysfs stores, I2C writes, raw MMIO access, selector reads/writes,
# or persistent filesystem mounts are performed by this collector.
PATH=/bin:/sbin
HOME=/
export PATH HOME

OUT=/run/g4-p2
mkdir -p "$OUT"

if ! test -r /proc/cmdline; then
    mount -t proc proc /proc
fi
if ! test -d /sys/bus/platform/devices; then
    mount -t sysfs sysfs /sys
fi
mkdir -p /sys/kernel/debug
if ! test -r /sys/kernel/debug/devices_deferred; then
    mount -t debugfs debugfs /sys/kernel/debug
fi

{
    echo "=== G4-P2 runtime identity ==="
    echo "uptime:"
    cat /proc/uptime
    echo
    echo "kernel:"
    uname -a
    echo
    echo "cmdline:"
    cat /proc/cmdline
    echo
    echo "device model:"
    cat /proc/device-tree/model
    echo
    echo "mounts:"
    mount
} > "$OUT/00-runtime.txt" 2>&1

{
    echo "=== IO-domain DT node and nine supply-property presence ==="
    NODE=/proc/device-tree/syscon@fdc20000/io-domains
    if test -d "$NODE"; then
        echo "IO-domain node: PRESENT"
        if test -e "$NODE/status"; then
            echo "status property: PRESENT (expected value okay)"
        else
            echo "status property: ABSENT (DT default applies)"
        fi
        for prop in pmuio1-supply pmuio2-supply vccio1-supply vccio2-supply \
                    vccio3-supply vccio4-supply vccio5-supply vccio6-supply vccio7-supply; do
            if test -e "$NODE/$prop"; then
                echo "SUPPLY PRESENT: $prop"
            else
                echo "ERROR: SUPPLY ABSENT: $prop"
            fi
        done
    else
        echo "ERROR: IO-domain DT node absent"
    fi
    echo
    echo "=== Isolation DT node statuses ==="
    for node in \
        /proc/device-tree/i2c@fdd40000/pmic@20 \
        /proc/device-tree/mmc@fe310000 \
        /proc/device-tree/mmc@fe2b0000 \
        /proc/device-tree/mmc@fe2c0000 \
        /proc/device-tree/gpu@fde60000 \
        /proc/device-tree/saradc@fe720000 \
        /proc/device-tree/ethernet@fe010000 \
        /proc/device-tree/ethernet@fe010000/mdio \
        /proc/device-tree/ethernet@fe010000/mdio/ethernet-phy@0; do
        echo
        echo "[$node]"
        if test -d "$node"; then
            if test -e "$node/status"; then
                echo "status property: PRESENT (see frozen DTB audit for value)"
            else
                echo "status property: ABSENT (DT default applies)"
            fi
        else
            echo "NODE ABSENT"
        fi
    done
} > "$OUT/10-device-tree.txt" 2>&1

{
    echo "=== IO-domain platform device enumeration and binding ==="
    DEV=/sys/bus/platform/devices/fdc20000.syscon:io-domains
    DRIVER=/sys/bus/platform/drivers/rockchip-iodomain
    echo "platform device:"
    if test -e "$DEV"; then
        ls -l "$DEV"
        if test -e "$DEV/driver"; then
            echo "driver link: PRESENT (driver bound)"
            ls -l "$DEV/driver"
        else
            echo "driver link: ABSENT (not bound)"
        fi
    else
        echo "platform device: ABSENT (child not enumerated under expected name)"
    fi
    echo
    echo "driver directory:"
    if test -d "$DRIVER"; then
        ls -l "$DRIVER"
    else
        echo "rockchip-iodomain driver directory: ABSENT"
    fi
    echo
    echo "parent PMUGRF platform device:"
    if test -e /sys/bus/platform/devices/fdc20000.syscon; then
        ls -l /sys/bus/platform/devices/fdc20000.syscon
    else
        echo "parent platform device path absent; syscon regmap may be consumer-created"
    fi
    echo
    echo "RK809 regulator provider binding:"
    REG=/sys/bus/platform/devices/rk808-regulator.3.auto
    if test -e "$REG"; then
        ls -l "$REG"
        if test -e "$REG/driver"; then
            ls -l "$REG/driver"
        else
            echo "rk808-regulator driver link: ABSENT"
        fi
    else
        echo "RK809 regulator platform device path absent"
    fi
    echo
    echo "Regulator class entries:"
    if test -d /sys/class/regulator; then
        ls -l /sys/class/regulator
        for item in /sys/class/regulator/regulator.*; do
            if test -e "$item/name"; then
                echo "[$item]"
                cat "$item/name"
                for field in state microvolts num_users; do
                    if test -r "$item/$field"; then
                        echo "$field:"
                        cat "$item/$field"
                    fi
                done
            fi
        done
    else
        echo "regulator class unavailable"
    fi
} > "$OUT/20-iodomain-and-regulator-binding.txt" 2>&1

{
    echo "=== Deferred probe state ==="
    if test -r /sys/kernel/debug/devices_deferred; then
        cat /sys/kernel/debug/devices_deferred
    else
        echo "devices_deferred unavailable"
    fi
} > "$OUT/30-deferred-probe.txt" 2>&1

dmesg > "$OUT/40-dmesg-full.txt" 2>&1
dmesg | tail -n 200 > "$OUT/41-dmesg-tail.txt" 2>&1

echo
echo "G4-P2 capture stored in RAM: $OUT"
echo "No persistent filesystem was mounted; no TF/eMMC files were written."
echo "No raw PMUGRF/PMIC register access was performed by this collector."
echo
echo "=== 10-device-tree.txt ==="
cat "$OUT/10-device-tree.txt"
echo
echo "=== 20-iodomain-and-regulator-binding.txt ==="
cat "$OUT/20-iodomain-and-regulator-binding.txt"
echo
echo "=== 30-deferred-probe.txt ==="
cat "$OUT/30-deferred-probe.txt"
echo
echo "=== 41-dmesg-tail.txt ==="
cat "$OUT/41-dmesg-tail.txt"

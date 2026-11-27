#!/bin/sh
# G3 runtime collector: RAM-only observations; no sysfs stores or PMIC writes.
PATH=/bin:/sbin
HOME=/
export PATH HOME

OUT=/run/g3-provider
mkdir -p "$OUT"

if [ ! -r /proc/cmdline ]; then
    mount -t proc proc /proc
fi
if [ ! -d /sys/bus/i2c/devices ]; then
    mount -t sysfs sysfs /sys
fi
mkdir -p /sys/kernel/debug
if [ ! -r /sys/kernel/debug/devices_deferred ]; then
    mount -t debugfs debugfs /sys/kernel/debug
fi

{
    echo "=== G3 RK809 regulator-provider runtime capture ==="
    echo "capture_time_uptime:"
    cat /proc/uptime
    echo
    echo "kernel:"
    uname -a
    echo
    echo "cmdline:"
    cat /proc/cmdline
    echo
    echo "device_model:"
    cat /proc/device-tree/model
    echo
    echo "mounts:"
    mount
} > "$OUT/00-runtime.txt" 2>&1

{
    echo "=== RK809 I2C parent and driver binding ==="
    ls -l /sys/bus/i2c/devices
    echo
    ls -l /sys/bus/i2c/devices/0-0020
    echo
    ls -l /sys/bus/i2c/devices/0-0020/driver
    echo
    echo "=== regulator platform devices ==="
    ls -l /sys/bus/platform/devices
    echo
    echo "=== regulator class ==="
    ls -l /sys/class/regulator
    for dev in /sys/class/regulator/regulator*; do
        [ -d "$dev" ] || continue
        echo
        echo "[$dev]"
        for attr in name num_users type state status microvolts; do
            if [ -r "$dev/$attr" ]; then
                echo "$attr:"
                cat "$dev/$attr"
            fi
        done
    done
} > "$OUT/10-regulator-devices.txt" 2>&1

{
    echo "=== regulator_summary (debugfs read-only observation) ==="
    if [ -r /sys/kernel/debug/regulator/regulator_summary ]; then
        cat /sys/kernel/debug/regulator/regulator_summary
    else
        echo "NOT AVAILABLE"
        ls -l /sys/kernel/debug
        ls -l /sys/kernel/debug/regulator
    fi
    echo
    echo "=== devices_deferred ==="
    if [ -r /sys/kernel/debug/devices_deferred ]; then
        cat /sys/kernel/debug/devices_deferred
    else
        echo "NOT AVAILABLE"
    fi
} > "$OUT/20-debugfs.txt" 2>&1

{
    echo "=== Device-tree isolation status ==="
    for node in \
        /proc/device-tree/i2c@fdd40000/pmic@20 \
        /proc/device-tree/syscon@fdc20000/io-domains \
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
        if [ -d "$node" ]; then
            if [ -r "$node/status" ]; then
                cat "$node/status"
                echo
            else
                echo "okay (implicit default)"
            fi
        else
            echo "NODE ABSENT"
        fi
    done
    echo
    echo "=== controller binding links (presence is not proof of probe) ==="
    for node in \
        /sys/bus/platform/devices/fe310000.mmc \
        /sys/bus/platform/devices/fe2b0000.mmc \
        /sys/bus/platform/devices/fe2c0000.mmc \
        /sys/bus/platform/devices/fdc20000.syscon:io-domains \
        /sys/bus/platform/devices/fde60000.gpu \
        /sys/bus/platform/devices/fe720000.saradc \
        /sys/bus/platform/devices/fe010000.ethernet; do
        echo
        echo "[$node]"
        if [ -e "$node" ]; then
            ls -l "$node"
            ls -l "$node/driver"
        else
            echo "device object absent"
        fi
    done
} > "$OUT/30-isolation.txt" 2>&1

dmesg > "$OUT/40-dmesg-full.txt" 2>&1
dmesg | tail -n 160 > "$OUT/41-dmesg-tail.txt" 2>&1

echo
echo "G3 capture written to RAM path: $OUT"
echo "No persistent filesystem was mounted; no files were written to TF/eMMC."
echo "Read-only capture files:"
ls -l "$OUT"
echo
echo "=== 00-runtime.txt ==="
cat "$OUT/00-runtime.txt"
echo
echo "=== 10-regulator-devices.txt ==="
cat "$OUT/10-regulator-devices.txt"
echo
echo "=== 20-debugfs.txt ==="
cat "$OUT/20-debugfs.txt"
echo
echo "=== 30-isolation.txt ==="
cat "$OUT/30-isolation.txt"
echo
echo "=== 41-dmesg-tail.txt ==="
cat "$OUT/41-dmesg-tail.txt"

# Panther X2 B1 clean RAM-only Linux baseline.
# U-Boot reads these three files from TF before Linux starts.
# Linux DTB deliberately disables all MMC/eMMC/TF, USB and network devices.
# This script never resets/reboots the board on a file-load failure.
setenv bootargs "console=ttyS0,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init"

echo "Panther X2 B1 clean RAM baseline"
echo "Boot source: ${devtype} ${devnum}"
echo "Loading Linux 6.18.63 clean Image..."

if load ${devtype} ${devnum} ${kernel_addr_r} /Image; then
    echo "Kernel Image loaded."
    if load ${devtype} ${devnum} ${ramdisk_addr_r} /uInitrd; then
        echo "RAM initramfs loaded."
        if load ${devtype} ${devnum} ${fdt_addr_r} /dtb/rockchip/rk3566-panther-x2.dtb; then
            echo "Preparing clean-test FDT..."
            fdt addr ${fdt_addr_r}
            fdt resize 65536
            echo "Starting B1 Linux with RAM initramfs..."
            booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}
        else
            echo "ERROR: Panther X2 clean-test DTB load failed; stopping without reset."
        fi
    else
        echo "ERROR: uInitrd load failed; stopping without reset."
    fi
else
    echo "ERROR: Kernel Image load failed; stopping without reset."
fi

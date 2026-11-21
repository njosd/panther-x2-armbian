# Panther X2 minimal RAM-only kernel test.
# This is loaded by the already-tested JP-TvBox U-Boot proper from TF partition 1.
setenv bootargs "console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init"

echo "Panther X2 minimal RAM-only test"
echo "Boot source: ${devtype} ${devnum}"
echo "Loading Linux 6.18.64 Image..."
if load ${devtype} ${devnum} ${kernel_addr_r} /Image; then
    echo "Loading RAM initramfs..."
else
    echo "ERROR: Image load failed"
    reset
fi
if load ${devtype} ${devnum} ${ramdisk_addr_r} /uInitrd; then
    echo "Loading Panther X2 DTB..."
else
    echo "ERROR: uInitrd load failed"
    reset
fi
if load ${devtype} ${devnum} ${fdt_addr_r} /dtb/rockchip/rk3566-panther-x2.dtb; then
    echo "Preparing FDT..."
else
    echo "ERROR: Panther X2 DTB load failed"
    reset
fi
fdt addr ${fdt_addr_r}
fdt resize 65536
echo "Starting Linux..."
booti ${kernel_addr_r} ${ramdisk_addr_r} ${fdt_addr_r}

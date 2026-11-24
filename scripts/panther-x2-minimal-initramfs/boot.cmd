# Panther X2 B1 clean RAM-only Linux baseline.
# Auto-discovered by the existing JP U-Boot distro boot scan on mmc1.
# Replays the exact manually verified TF device, RAM addresses and bootargs.
# No environment is saved; no persistent storage is written.
# If any step fails, hold here instead of falling through to eMMC/PXE/DHCP.
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init'

echo "Panther X2 B1 automatic clean RAM boot"
echo "Selecting verified SU08G TF device: mmc 1"
if mmc dev 1; then
    if load mmc 1:1 0x00280000 /Image; then
        echo "Kernel Image loaded at 0x00280000."
        if load mmc 1:1 0x0a200000 /uInitrd; then
            echo "RAM initramfs loaded at 0x0a200000."
            if load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb; then
                echo "Panther X2 DTB loaded at 0x0a100000."
                echo "Starting B1 Linux..."
                booti 0x00280000 0x0a200000 0x0a100000
                echo "ERROR: booti returned; automatic fallback is blocked."
            else
                echo "ERROR: Panther X2 DTB load failed; automatic fallback is blocked."
            fi
        else
            echo "ERROR: uInitrd load failed; automatic fallback is blocked."
        fi
    else
        echo "ERROR: Kernel Image load failed; automatic fallback is blocked."
    fi
else
    echo "ERROR: mmc dev 1 failed; automatic fallback is blocked."
fi

while true; do
    sleep 10
done

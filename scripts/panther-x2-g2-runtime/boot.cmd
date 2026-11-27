# Panther X2 Project-A G2 safe minimal runtime.
# Existing eMMC SPL -> JP-TvBox U-Boot proper from TF -> Linux Image/uInitrd/DTB from TF.
# The Linux DTB keeps RK809, GMAC1, MDIO and RTL8211F disabled.
# No environment is saved. Any load/boot failure holds here; no reset or fallback.
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init'
setenv boot_targets 'mmc1'

echo "Panther X2 Project-A G2 minimal runtime (PREPARE-ONLY)"
echo "Selecting verified TF device: mmc 1"
if mmc dev 1; then
    if load mmc 1:1 0x00280000 /Image; then
        echo "Linux Image loaded at 0x00280000."
        if load mmc 1:1 0x0a200000 /uInitrd; then
            echo "RAM initramfs loaded at 0x0a200000."
            if load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb; then
                echo "Panther X2 G2 safe DTB loaded at 0x0a100000."
                echo "Starting Linux with RAM initramfs; PMIC and GMAC remain disabled."
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

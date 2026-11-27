# Panther X2 Project-A G3 RK809 regulator-provider runtime.
# Existing eMMC SPL -> JP-TvBox U-Boot proper from SU08G -> Image/uInitrd/DTB from SU08G.
# This boots only the G3 isolated DTB; no environment is saved and no fallback/reset occurs.
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init regulator_ignore_unused'

echo "Panther X2 Project-A G3 RK809 regulator-provider runtime (PREPARE-ONLY)"
echo "Selecting verified experiment TF device: mmc 1"
if mmc dev 1; then
    if load mmc 1:1 0x00280000 /Image; then
        echo "Linux Image loaded at 0x00280000."
        if load mmc 1:1 0x0a200000 /uInitrd; then
            echo "G3 RAM initramfs loaded at 0x0a200000."
            if load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb; then
                echo "G3 isolated Panther X2 DTB loaded at 0x0a100000."
                echo "Starting Linux; RK809 regulator provider probe and expected PMIC writes will occur."
                echo "IO-domain/MMC/SDIO/GPU/SARADC/GMAC consumers remain disabled."
                booti 0x00280000 0x0a200000 0x0a100000
                echo "ERROR: booti returned; automatic fallback is blocked."
            else
                echo "ERROR: G3 DTB load failed; automatic fallback is blocked."
            fi
        else
            echo "ERROR: G3 uInitrd load failed; automatic fallback is blocked."
        fi
    else
        echo "ERROR: G3 kernel Image load failed; automatic fallback is blocked."
    fi
else
    echo "ERROR: mmc dev 1 failed; automatic fallback is blocked."
fi

while true; do
    sleep 10
done

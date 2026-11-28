# Panther X2 Project-A G4-P2 full-supply IO-domain runtime; PREPARE-ONLY.
# Existing eMMC SPL -> JP-TvBox U-Boot proper from SU08G -> Image/uInitrd/DTB from SU08G.
# Full nine-supply IO-domain consumer probe is enabled.
# GMAC1, MDIO and RTL8211F remain disabled.
# No environment is saved; load/boot failures hold here without reset/fallback.
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init regulator_ignore_unused'

echo "Panther X2 Project-A G4-P2 full-supply IO-domain runtime (PREPARE-ONLY)"
echo "Selecting verified experiment TF device: mmc 1"
if mmc dev 1; then
    if load mmc 1:1 0x00280000 /Image; then
        echo "G4-P2 Linux Image loaded at 0x00280000."
        if load mmc 1:1 0x0a200000 /uInitrd; then
            echo "G4-P2 RAM initramfs loaded at 0x0a200000."
            if load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb; then
                echo "G4-P2 Panther X2 DTB loaded at 0x0a100000."
                echo "Starting Linux: IO-domain probe may read regulator voltage,"
                echo "register notifiers and write PMU GRF selector fields."
                echo "GMAC1/MDIO/PHY remain disabled; no network TX is attempted."
                booti 0x00280000 0x0a200000 0x0a100000
                echo "ERROR: booti returned; automatic fallback is blocked."
            else
                echo "ERROR: G4-P2 DTB load failed; automatic fallback is blocked."
            fi
        else
            echo "ERROR: G4-P2 uInitrd load failed; automatic fallback is blocked."
        fi
    else
        echo "ERROR: G4-P2 kernel Image load failed; automatic fallback is blocked."
    fi
else
    echo "ERROR: mmc dev 1 failed; automatic fallback is blocked."
fi

while true; do
    sleep 10
done

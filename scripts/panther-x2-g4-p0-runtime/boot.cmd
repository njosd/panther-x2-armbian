# Panther X2 Project-A G4-P0 binding-only runtime; PREPARE-ONLY.
# Existing eMMC SPL -> JP-TvBox U-Boot proper from SU08G -> Image/uInitrd/DTB from SU08G.
# RK809 provider remains enabled (same PMIC initialization side effects as G3).
# IO-domain child is enabled but all nine supply properties are absent.
# No environment is saved; load/boot failures hold here without reset/fallback.
setenv bootargs 'console=ttyS02,1500000 earlycon loglevel=8 ignore_loglevel printk.time=1 rdinit=/init regulator_ignore_unused'

echo "Panther X2 Project-A G4-P0 binding-only runtime (PREPARE-ONLY)"
echo "Selecting verified experiment TF device: mmc 1"
if mmc dev 1; then
    if load mmc 1:1 0x00280000 /Image; then
        echo "G4-P0 Linux Image loaded at 0x00280000."
        if load mmc 1:1 0x0a200000 /uInitrd; then
            echo "G4-P0 RAM initramfs loaded at 0x0a200000."
            if load mmc 1:1 0x0a100000 /dtb/rockchip/rk3566-panther-x2.dtb; then
                echo "G4-P0 Panther X2 DTB loaded at 0x0a100000."
                echo "Starting Linux: RK809 provider probe may initialize PMIC registers."
                echo "IO-domain probe is expected to acquire PMUGRF regmap without selector transactions."
                booti 0x00280000 0x0a200000 0x0a100000
                echo "ERROR: booti returned; automatic fallback is blocked."
            else
                echo "ERROR: G4-P0 DTB load failed; automatic fallback is blocked."
            fi
        else
            echo "ERROR: G4-P0 uInitrd load failed; automatic fallback is blocked."
        fi
    else
        echo "ERROR: G4-P0 kernel Image load failed; automatic fallback is blocked."
    fi
else
    echo "ERROR: mmc dev 1 failed; automatic fallback is blocked."
fi

while true; do
    sleep 10
done

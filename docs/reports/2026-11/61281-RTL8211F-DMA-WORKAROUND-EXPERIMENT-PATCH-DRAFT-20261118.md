# Panther X2：6.12.81 对照 6.1.116 workaround 实验补丁草案

日期：2026-11-18  
目标源码：`ophub/linux-6.12.y-rockchip`  
固定基线：`661b2d8bf1284556f8876d5ed5fb80c64b22f94c`  
状态：**补丁草案；尚未编译、尚未实机验证；不得用于现有生产启动项。**

## 1. 本轮源码核查结果

- `CONFIG_STMMAC_ETH=y`：目标 `arch/arm64/configs/rockchip_linux_defconfig` 将 STMMAC 编入内核。
- `mdiobus_get_phy(bus, addr)` 声明位于 `include/linux/mdio.h`，实现位于 `drivers/net/phy/mdio_bus.c`。它从 `bus->mdio_map[]` 返回 PHY 指针，不增加引用计数。实验在 MDIO 注册流程内同步执行，不应额外 put。
- `phy_read_paged()` / `phy_write_paged()` 通过 `phy_select_page()` 和 `phy_restore_page()` 管理页选择及 MDIO 锁；失败时返回负 errno，成功写返回 0。
- `phy_read_poll_timeout()` 可用，底层读取出错会提前返回错误；本补丁使用 50ms 轮询间隔、600ms 上限。
- `of_mdiobus_register()` 成功后，PHY 已注册并完成同步 probe；此时尚未进入后续 PHY attach/config_init。插入点与 116 workaround 的原始位置相同：注册成功后、`priv->mii = new_bus` 之前。
- 后续 RTL8211F `config_init()` 仍会运行：它会依据 probe 时缓存的 CLKOUT_EN 状态修改 PHYCR2 bit 0，并执行 `genphy_soft_reset()`。因此模式 1/2 的注入后读回值不等于驱动初始化完成后的最终寄存器状态。
- DMA 延时严格位于 `stmmac_reset()` 之前；函数可能在恢复路径再次调用，故 1500ms 参数可能在每次进入该函数时生效。

## 2. 补丁 diff（仅两个源文件）

目标文件：
- `drivers/net/ethernet/stmicro/stmmac/stmmac_mdio.c`
- `drivers/net/ethernet/stmicro/stmmac/stmmac_main.c`

### stmmac_mdio.c

在 include 区增加：

```diff
+#include <linux/moduleparam.h>
```

在 `stmmac_pcs_clean()` 函数之后、`stmmac_mdio_register()` 之前增加：

```c
#define STMMAC_TEST_RTL8211F_ID       0x001cc916
#define STMMAC_TEST_RTL8211F_PAGE     0x0a43
#define STMMAC_TEST_RTL8211F_PHYCR2   0x19
#define STMMAC_TEST_RTL8211F_VALUE    0x1801

static int phycr2_test;
module_param_named(phycr2_test, phycr2_test, int, 0444);
MODULE_PARM_DESC(phycr2_test,
        "RTL8211F test: 0=off, 1=write/read, 2=write/read/BMCR reset");

static void stmmac_rtl8211f_test(struct device *dev, struct mii_bus *bus)
{
        struct phy_device *phydev;
        int ret, readback, bmcr;

        if (!phycr2_test)
                return;

        if (phycr2_test < 0 || phycr2_test > 2) {
                dev_warn(dev, "RTL8211F test: invalid mode %d, skipped\n",
                         phycr2_test);
                return;
        }

        phydev = mdiobus_get_phy(bus, 0);
        if (!phydev) {
                dev_warn(dev, "RTL8211F test: PHY address 0 not found\n");
                return;
        }

        if (phydev->phy_id != STMMAC_TEST_RTL8211F_ID) {
                dev_warn(dev,
                         "RTL8211F test: PHY ID mismatch at address 0: %08x\n",
                         phydev->phy_id);
                return;
        }

        dev_info(dev, "RTL8211F test: mode=%d PHY ID=%08x address=0\n",
                 phycr2_test, phydev->phy_id);

        ret = phy_write_paged(phydev, STMMAC_TEST_RTL8211F_PAGE,
                              STMMAC_TEST_RTL8211F_PHYCR2,
                              STMMAC_TEST_RTL8211F_VALUE);
        if (ret < 0) {
                dev_err(dev, "RTL8211F test: PHYCR2 write failed: %d\n",
                        ret);
                return;
        }

        readback = phy_read_paged(phydev, STMMAC_TEST_RTL8211F_PAGE,
                                  STMMAC_TEST_RTL8211F_PHYCR2);
        if (readback < 0) {
                dev_err(dev, "RTL8211F test: PHYCR2 readback failed: %d\n",
                        readback);
                return;
        }

        dev_info(dev,
                 "RTL8211F test: PHYCR2 write_ret=%d immediate_readback=0x%04x\n",
                 ret, readback);

        if (phycr2_test == 1)
                return;

        ret = phy_write(phydev, MII_BMCR, BMCR_RESET);
        if (ret < 0) {
                dev_err(dev, "RTL8211F test: BMCR reset write failed: %d\n",
                        ret);
                return;
        }

        ret = phy_read_poll_timeout(phydev, MII_BMCR, bmcr,
                                    !(bmcr & BMCR_RESET),
                                    50000, 600000, true);
        if (ret)
                dev_err(dev,
                        "RTL8211F test: BMCR reset poll failed: %d, last BMCR=0x%04x\n",
                        ret, bmcr);
        else
                dev_info(dev,
                         "RTL8211F test: BMCR reset completed, BMCR=0x%04x\n",
                         bmcr);

        readback = phy_read_paged(phydev, STMMAC_TEST_RTL8211F_PAGE,
                                  STMMAC_TEST_RTL8211F_PHYCR2);
        if (readback < 0)
                dev_err(dev,
                        "RTL8211F test: PHYCR2 post-reset read failed: %d\n",
                        readback);
        else
                dev_info(dev,
                         "RTL8211F test: PHYCR2 post-reset readback=0x%04x\n",
                         readback);
}
```

在 `of_mdiobus_register()` 成功返回后、XGMAC dummy read 之前增加：

```diff
+       if (!priv->plat->has_xgmac)
+               stmmac_rtl8211f_test(dev, new_bus);
+
        /* Looks like we need a dummy read for XGMAC only and C45 PHYs */
        if (priv->plat->has_xgmac)
                stmmac_xgmac2_mdio_read_c45(new_bus, 0, 0, 0);
```

### stmmac_main.c

在 include 区增加：

```diff
+#include <linux/delay.h>
+#include <linux/moduleparam.h>
```

在现有模块参数区增加：

```c
static int dma_delay_ms;
module_param_named(dma_delay_ms, dma_delay_ms, int, 0444);
MODULE_PARM_DESC(dma_delay_ms,
        "Experimental delay before stmmac DMA reset: 0 or 1500 ms");
```

在 `stmmac_init_dma_engine()` 中，原有 `stmmac_reset()` 之前增加：

```c
        if (dma_delay_ms == 1500) {
                dev_info(priv->device,
                         "Experimental DMA reset delay: 1500 ms\n");
                msleep(1500);
        } else if (dma_delay_ms != 0) {
                dev_warn(priv->device,
                         "Invalid experimental DMA delay %d ms; ignored\n",
                         dma_delay_ms);
        }

        ret = stmmac_reset(priv, priv->ioaddr);
```

## 3. 参数及实验矩阵

内核命令行参数（built-in STMMAC）：

```
stmmac.phycr2_test=0 stmmac.dma_delay_ms=0
```

| 组别 | phycr2_test | dma_delay_ms | 目的 |
|---|---:|---:|---|
| A | 0 | 0 | 实验内核原始行为对照 |
| B | 1 | 0 | 仅 PHYCR2 写入并立即读回 |
| C | 2 | 0 | PHYCR2 写入、读回及 BMCR reset |
| D | 0 | 1500 | 仅 DMA reset 前延时 |
| E | 2 | 1500 | 两项组合 |

每轮均需采集：启动参数、内核版本和启动日志、PHY ID、PHYCR2 写入返回值、即时读回、BMCR reset 完成/超时、reset 后读回、后续 PHY link/config_init 日志、链路协商结果、DHCP Discover/Offer/Request/ACK 完整过程、网卡 TX/RX 计数器及抓包证据。每个看似成功的组别至少重复验证，不能以单次 DHCP 成功判定修复。

## 4. 风险与回退

- 模式 1/2 会改变 RTL8211F PHYCR2；模式 2 还会触发 PHY soft reset，链路会短暂中断并重新协商。
- 1500ms 延时会增加 DMA 初始化时间；不应在已有服务运行的生产内核上动态启用。
- 参数默认均为 0，默认行为不变。
- 必须从独立测试内核启动；现有 6.1.116/当前可启动内核、DTB、initrd、启动配置和启动介质内容均保留原样。
- 测试失败时重启回原有启动项；不覆盖原内核、不改默认启动项、不写入生产内核目录。
- 当前未获得设备终端连接，未执行实机写入或重启。

## 5. 尚未完成的验证

1. 尚未应用此 diff 到工作树，尚未运行编译器。
2. 尚未核实实际构建所用 defconfig、交叉编译器、工具链和完整构建配置是否与上述 `rockchip_linux_defconfig` 一致。
3. 尚未确认 Panther X2 当前启动介质和启动管理器支持的独立测试启动方式。
4. 尚未生成可启动镜像、未进行实机测试。

**结论：这是一份用于构建独立实验内核的源码补丁草案，不是修复补丁，不代表已证明 PHYCR2 或 DMA 延时能修复 DHCP 故障。**

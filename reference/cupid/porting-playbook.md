# 小米12 (cupid) 主线 Linux 移植手册（可复现）

> 目的：从零复现最终单系统方案。设计说明见 `docs/architecture.md`，
> 当前限制见 `docs/known-issues.md`；本文只给命令、配置和坑。
> 最后更新：2026-11-01 23:45。

## 0. 当前形态快照

| 项 | 值 |
|---|---|
| 内核 | `7.2.8-cupid+`，build `#96`（`out/boot-v78.img`，sha256 `568b2c8e…`） |
| 启动 | 直接写 `boot_a`（`/dev/sde14`），开机即进 Linux，无需电脑 |
| 根 | `/dev/sda38`（原 userdata，222 GB），ext4 label `linux`，219 G / 可用 213 G |
| 根标记 | `/etc/cupid-rootfs-release` = `cupid-ubuntu-phosh-v1`，`/etc/cupid-rootfs-version` = `cupid-ubuntu-phosh-v7` |
| 桌面 | Ubuntu 26.04 arm64 + Phosh；`zh_CN.UTF-8`、`Asia/Shanghai`；902 个包 |
| 远程 | wayvnc 0.5 + noVNC，`http://<手机IP>:6080/vnc.html` |
| Android | 已随 userdata 格式化移除；回退靠备份 boot_a |

## 1. 环境

- **内核树只在 WSL `/root/linux`**（ext4）。Windows 侧 `kernel/` 已分叉，不要用。
- 工具链：`aarch64-linux-gnu-gcc`；`export PATH=/usr/lib/ccache:$PATH`。
- Windows 侧：`fastboot`（adb2 改名副本）、`out/magiskboot-x64/magiskboot.exe`、
  `tools/mkbootimg/mkbootimg.py`。
- 构建产物 `out/`，备份和本机唯一数据 `private/`（不进仓库）。

## 2. 内核配置（决定能否启动）

```
CONFIG_CUPID_FORCE_BUILTIN_DTB=y          # 用内嵌主线 DTB 覆盖 __fdt_pointer
CONFIG_INITRAMFS_SOURCE="/root/initramfs-cupid-v26"   # initramfs 编进内核
# CONFIG_CPU_IDLE is not set               # 开了会黑屏
CONFIG_PINCTRL_QCOM_SPMI_PMIC=y
CONFIG_POWER_RESET_QCOM_PON=y
CONFIG_RTC_CLASS=y
CONFIG_RTC_DRV_PM8XXX=y
CONFIG_INPUT_PM8941_PWRKEY=y
CONFIG_KEYBOARD_GPIO=y
```

为什么必须这样（细节见 `docs/architecture.md`）：

1. **ABL 只认 v2 头**，且 DTB 根身份必须是 `qcom,msm-id = <0x1c9 0x10000>`（waipio）、
   `qcom,board-id = <0 0>`；boot.img 的 dtb 字段放**原厂 6.2 MB 多 DTB 容器**
   （`out/v47-inspect/dtb`）当“诱饵”，ABL 校验/叠加它，内核再用内建 DTB 覆盖。
2. 内建 DTB 后 **cmdline 唯一来源 = DTB 的 `/chosen/bootargs`**（mkbootimg `--cmdline` 失效）。
3. 内建 DTB 后 **initramfs 必须编进内核**（`CONFIG_INITRAMFS_SOURCE`）。
4. `__symbols__` 必须覆盖 dtbo/hypervisor overlay 的全部 fixup 符号（1518 个符号的并集）。

## 3. 构建内核

```bash
cd /root/linux
export PATH=/usr/lib/ccache:$PATH

# 1) 生成板级 DTB（v78 用 sm8450-xiaomi-cupid-v-touch）
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DTC_FLAGS='-@' \
     qcom/sm8450-xiaomi-cupid-v-touch.dtb

# 2) 编 Image，CUPID_DTB 指定内建 DTB
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     CC='ccache aarch64-linux-gnu-gcc' \
     CUPID_DTB=sm8450-xiaomi-cupid-v-touch -j8 Image

cp arch/arm64/boot/Image "$REPO/out/Image-vXX"   # REPO=本仓库根目录
```

initramfs（PID1 用静态 C，busybox 只给串口 shell）：

```bash
R=/root/initramfs-cupid-v26
mkdir -p $R/{bin,sbin,etc,proc,sys,dev/pts,tmp,run,newroot}
install -m 0755 /mnt/c/.../out/busybox-aarch64 $R/bin/busybox
aarch64-linux-gnu-gcc -static -Wall -Wextra -Werror -O2 \
    -o $R/init /mnt/c/.../tools/initramfs/init_static_v21.c
scripts/config --set-str INITRAMFS_SOURCE "$R"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
```

## 4. 打包 boot.img

```bash
python3 tools/mkbootimg/mkbootimg.py \
  --kernel out/Image-vXX \
  --dtb out/v47-inspect/dtb \
  --header_version 2 --pagesize 2048 \
  --base 0x00000000 --kernel_offset 0x10008000 \
  --ramdisk_offset 0x00000000 --tags_offset 0x10000100 \
  --dtb_offset 0x11f00000 \
  --output out/boot-vXX.img
```

- **不要**加 `--ramdisk`：initramfs 已在 Image 里。
- 原厂 boot.img 的 v2 头、pagesize 2048、上述 offset 是实测值。

## 5. 刷入、校验与回退

**首次写入前必须**：备份目标分区（整分区 + 双端哈希一致），恢复镜像在手。

```bash
# Linux 侧直接写（boot_a = /dev/sde14）
dd if=/tmp/boot-vXX.img of=/dev/sde14 bs=1048576 conv=fsync
sync
dd if=/dev/sde14 bs=2048 count=21490 2>/dev/null | sha256sum   # v78: 21490*2048 = 44011520 字节
```

```powershell
# Windows 侧 fastboot
fastboot flash boot_a out\boot-vXX.img
fastboot reboot
```

回退：

1. `fastboot flash boot_a private/backup/boot_a-current-20261101-221347.img`
   （sha256 `f86412f4…`，第三方 ROM 的启动镜像；userdata 已格式化，Android 数据不可恢复）。
2. 槽位被标 unbootable 时：`fastboot set_active a`，再恢复 `private/backup/misc.img`
   （`f4d714ba…`）。
3. `recovery_a` 的 TWRP 未改动（`7674779c…`），仍可进 recovery。

## 6. 根文件系统

- 发行版：Ubuntu 26.04 arm64（minbase）+ Phosh；构建目录 WSL `/root/rootfs-phosh-v1`，
  覆盖层 `tools/rootfs-phosh/overlay-v7/`。
- 部署：`mkfs.ext4 -L linux /dev/sda38` → 挂载 → `cp -a` → 写
  `/etc/cupid-rootfs-release`。
- init v21 的根发现顺序（`tools/initramfs/init_static_v21.c`）：
  1. `PARTNAME=userdata` 且 ext4 卷标 `linux`；
  2. 回退 `PARTNAME=cust` + 固定 4194304 扇区；
  两者都要求 ext4 超级块有效 + 标记文件匹配。
- `/etc/fstab` 为空是正常的：root 由 init 直接挂好。
- 完整应用集：设备上 `/usr/local/sbin/cupid-install-apps`（902 包）。
- 时间：PMIC RTC 写被 SPMI arbiter 封锁（`disallowed SPMI write ... 0x6146`），
  用 `cupid-timesync.timer` 走 NTP；`cupid-rtc-save.timer` 必须保持 disabled。

## 7. 硬件打通要点

| 子系统 | 关键结论 |
|---|---|
| 面板 | Novatek DSC **range0 max_qp=8**（默认 PRE_SCR=4 会花屏）；只暴露 **120Hz**（clock 349670 kHz，vtotal 2512）；息屏 0x28+0x10，亮屏 0x11→PPS→0x29；**rails 常开** |
| GPU | Adreno 730 / freedreno，GPU 合成可用；动态内容横条噪声未解 |
| 调频 | 3 簇 cpufreq + thermal 正常 |
| 电池 | ADSP battmgr over pmic_glink；SM8450 固件把 `BATT_CONSTANT_CURRENT` 放在 id 12（温度是 13）；`current_sign_flip` 仅 sm8475 |
| USB | 复合 ACM+RNDIS，`1d6b:0104`；`usb0` = 192.168.137.2 / 172.16.42.2；**不要加默认路由** |
| WiFi | ath11k WCN6855；2.4G/5G 扫描可用；5G 信号弱（通用 board 校准，挂起） |
| 触摸 | ST FTM5（SPI） |
| 按键 | 电源键 PMIC PON，音量键 PMIC GPIO pinctrl |
| 传感器/音频/GPS | 未做（SSC/CS35L41/WCD938x） |

## 8. 已知坑（按代价排序）

1. **60/90Hz 切换会挂死**（`modetest -s 36:1080x2400-90` → 整机重启）。只暴露 120Hz。
2. **系统挂起 `echo freeze` 会挂死**：CPU_IDLE 关闭、apps_rsc power-domains 被删、USB 非 wakeup
   source。恢复需长按电源 10–15 秒。
3. **RTC 写被 SPMI arbiter 拒绝**：只能读，校时用 NTP。
4. **Chromium GPU 加速会挂死设备**：默认 `--disable-gpu`。
5. **wayvnc 0.9 抓帧不可用**：`ext-image-copy-capture` 无匹配格式（`-g` 抓到纯灰）；
   用 0.5 的 `wlr-screencopy`。
6. **snapd 不可用**：内核无 squashfs、无 AppArmor LSM。
7. **Debian chromium 安装坑**：`chromium-common`/`chromium-sandbox` 必须与 `chromium`
   完全同版本；`apt-get -f install` 会直接移除 chromium；`libjpeg62-turbo` 要从 Debian 装。
8. **`pkill -f` 会杀掉串口脚本自己**（模式匹配到脚本命令行），用 `pkill -x`。
9. **USB gadget 可能整体消失**：串口 + RNDIS 全无时先长按电源；不要反复刷写。
10. **电量门**：离开 Android / 长时间试验前电量 ≥40%；多次失败启动会快速耗电。

## 9. 远程桌面（当前可用）

```ini
# /etc/systemd/system/wayvnc.service
[Service]
User=linux
Environment=XDG_RUNTIME_DIR=/run/user/1000
Environment=WAYLAND_DISPLAY=wayland-0
ExecStart=/usr/bin/wayvnc -g -o DSI-1 -f 120 0.0.0.0 5900
```

```ini
# /etc/systemd/system/novnc.service
[Service]
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 6080 127.0.0.1:5900
```

- `novnc.service` 用 `Wants=wayvnc.service`，**不要用 `Requires=`**（重启 wayvnc 会把 noVNC 停掉）。
- 浏览器：`http://<手机IP>:6080/vnc.html?autoconnect=true&resize=scale`
- 无密码，仅局域网；`-f 120` 是上限，实际受 CPU/带宽限制。
- IP 会变（DHCP）：手机「设置 → Wi-Fi」查看。`cupid.local` 仅手机侧可解析
  （Windows 代理 DNS 会返回 198.18.x.x）。

## 10. 文档索引

| 文件 | 内容 |
|---|---|
| `docs/architecture.md` | 启动链、显示、电源、网络、根文件系统的最终设计 |
| `docs/known-issues.md` | 当前限制、规避方式、后续方向 |
| `docs/hardware-list.md` | 硬件清单（面板/触控/音频/WiFi/充电/传感器） |
| `docs/panel-commands.md` / `panel-timings.md` | 面板 DCS 命令表与时序 |
| `docs/reference/dt-compatibles.txt` | 运行时 DT 全量 compatible |
| `tools/` | 构建、打包、部署、串口与验证脚本（build-final.sh、deploy-rootfs.ps1 等） |

## 11. 设备安全门（每次操作）

1. 同一时刻只有一个操作者；每条设备命令带 serial。
2. 风险递进：只读 → 内存启动 → 写分区 → 改 bootloader 状态。
3. 写前备份，双端哈希一致；恢复镜像在手才做持久写入。
4. A/B 槽状态只用 bootloader 自己的命令改（`fastboot set_active`），不手写属性位。
5. 序列号、MAC、蓝牙地址、校准数据、备份、密码只放 `private/`，不进仓库。
6. 离开 Android 前读电量（≥40%）。

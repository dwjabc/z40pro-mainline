# 系统架构（终版）

> 本文描述**当前可用**的单系统方案。历史试验与失败路径不在本仓库。

## 启动链

```
ABL (bootloader)
  └─ boot_a: boot.img (header v2, pagesize 2048)
       ├─ kernel: Image (7.2.8-cupid+)
       │    ├─ CONFIG_CUPID_FORCE_BUILTIN_DTB: 用内建 DTB 覆盖 __fdt_pointer
       │    └─ CONFIG_INITRAMFS_SOURCE: initramfs 编进内核
       └─ dtb: 原厂 6.2 MB 多 DTB 容器（“诱饵”，只用于通过 ABL 校验/叠加）
            └─ 内核启动后改用内建主线 DTB（cmdline 只来自它的 /chosen/bootargs）
```

关键约束：

1. ABL 只接受 **v2 header**，DTB 根身份必须是 `qcom,msm-id = <0x1c9 0x10000>`（waipio）、
   `qcom,board-id = <0 0>`。
2. 内建 DTB 后 mkbootimg 的 `--cmdline` 失效，启动参数写在板级 DTS 的 `/chosen/bootargs`。
3. `__symbols__` 必须覆盖原厂 dtbo/hypervisor overlay 引用的全部 fixup 符号
   （`sm8450-xiaomi-cupid-syms.dtsi`）。
4. boot_a 是 192 MiB，最终镜像约 44 MB；recovery_a 是 ramdisk-only TWRP，
   不能承载内核（ABL 启动 recovery 时内核固定取 boot 分区）。

## initramfs 与根发现

PID1 是静态编译的 `init_static_v21.c`（纯 syscall，busybox 只提供串口 shell）。
它按顺序找根：

1. GPT `PARTNAME=userdata` 且 ext4 卷标为 `linux`；
2. 回退 GPT `PARTNAME=cust`（固定 4194304 扇区）且卷标为 `linux`。

两个条件都要求 ext4 超级块有效，并校验 `/etc/cupid-rootfs-release` 标记。
找到后挂载、切换 root、启动 systemd；串口控制台保持可用（`root` 无密码，仅开发期）。

## 存储布局

| 分区 | 设备 | 用途 |
|---|---|---|
| `boot_a` | `/dev/sde14` | 主线 kernel + 诱饵 DTB（44 MB） |
| `userdata` | `/dev/sda38` | Linux 根，ext4 label `linux`，222 GB |
| `cust` | `/dev/sda27` | 旧 2 GiB 根，保留作 init 回退 |
| `recovery_a` | — | TWRP，未改动 |

`/etc/fstab` 为空：根由 init 直接挂载，systemd 不需要 fstab 条目。

## 显示

- 面板：1080x2400 AMOLED，Novatek 驱动 IC，DSC 1.1。
- **DSC 第 0 档 `max_qp = 8`**（主线默认 4 会横向花屏）；不要切 DSC 1.2 表。
- 只暴露 **120Hz**（clock 349670 kHz，vtotal 2512）。60/90Hz 切换会挂死（见 known-issues）。
- 息屏：DCS `0x28` + `0x10`；亮屏：`0x11` → PPS → `0x29`。
- 面板供电（vddio/vddd/vci）在息屏期间**保持开启**：本板尚未完成完全自初始化，
  断电后 prepare 阶段无法重新点亮。
- GPU：Adreno 730 / freedreno，Phosh 使用 GPU 合成。

## 电源、电池与热

- 电池：ADSP battmgr over `pmic_glink`，提供容量/电压/电流/温度/状态。
- SM8450 固件把 `BATT_CONSTANT_CURRENT` 放在属性 id 12（温度是 id 13），
  `qcom_battmgr.c` 按机型修正；充电电流符号单独处理。
- `CONFIG_CPU_IDLE` 必须关闭（开启会黑屏）。
- 热保护：`CPU_THERMAL` / `DEVFREQ_THERMAL` / `STEP_WISE`，90/95°C 降频、110°C critical。
- PMIC RTC 可读，写被 SPMI arbiter 封锁；校时用 NTP（`cupid-timesync.timer`）。

## 网络与远程桌面

- USB 复合设备：ACM 串口 + RNDIS，`1d6b:0104`；`usb0` 固定 `192.168.137.2/24`、
  `172.16.42.2/24`，**不设默认路由**。
- WiFi：ath11k / WCN6855（PCIe），NetworkManager 管理；2.4G/5G 扫描可用。
- 远程桌面：wayvnc 0.5（wlr-screencopy）+ websockify/noVNC。
  `wayvnc -g -o DSI-1 -f 120 0.0.0.0 5900`，`websockify --web=/usr/share/novnc 6080 127.0.0.1:5900`。
  浏览器打开 `http://<手机IP>:6080/vnc.html?autoconnect=true&resize=scale`。
- `-f 120` 只是上限；实际帧率受 CPU 与带宽限制（1080x2400 原始帧约 10 MB）。

## 根文件系统

- Ubuntu 26.04 arm64（minbase）+ Phosh；`zh_CN.UTF-8`、`Asia/Shanghai`。
- 构建流程：`tools/rootfs-phosh/prepare-rootfs.sh` → `install-packages.sh` →
  `configure-rootfs.sh` → 部署后 `apply-v7.sh`。
- 完整应用集（902 包）通过设备上的 `apt` 安装；关键应用：Chromium 156（Debian deb，
  `--disable-gpu`）、xfce4-terminal、Nautilus、Epiphany、Loupe、GNOME 工具集。
- 开发期串口登录：`root` 无密码；发布前必须关闭或改密码。

## 回退

- 启动回 Android：`fastboot flash boot_a private/backup/boot_a-current-*.img`
  （Android userdata 已被格式化，数据不可恢复）。
- 旧 Linux 根：boot_a 换回 v77 镜像，init 回退到 `cust`。
- `recovery_a` 的 TWRP 未改动。
- 槽位被标 unbootable：`fastboot set_active a`，恢复 `misc` 备份。

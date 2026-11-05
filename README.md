# z40pro-mainline

Nubia Z40 Pro (NX701J, SM8450) mainline Linux 移植工程。

## 当前状态 (v0.1)
- 目标: `boot.img` 心跳 — 内核起来、USB gadget NCM 起网卡、telnetd 可达
- 面板: Visionox RM692E5 (mainline `panel-visionox-rm692e5` 已有驱动, M5 点亮)
- 触摸: FocalTech (待移植)
- rootfs: 待常驻 (M6)

## 结构
- `kernel-patch/` — 设备树 + config fragment
- `scripts/` — CI 构建辅助 (Makefile 注入 / initramfs / boot.img 组装)
- `initramfs/` — 调试 init (USB NCM + telnetd)
- `tools/` — 救砖包 dtbo/DTS 解析工具 (纯 Python)

## 刷写
CI 产出 `boot.img` 后, 用 9008 EDL 写 boot_a (备份 boot_a_current_backup.img 兜底):
```
python edl.py --loader prog_ufs_firehose.elf w boot_a boot.img
```

## 调试
- USB NCM: PC 配 192.168.237.1 → `telnet 192.168.237.2` (需 Windows 侧安装 RNDIS/NCM 驱动识别)
- ramoops: 0xffc00000 (2MB), panic 后重启可经 pstore/EDL 取日志

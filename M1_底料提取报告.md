# M1 底料提取报告 — Z40 Pro (NX701J) mainline 移植素材

日期: 2026-11-05  |  工具: 07_root/mainline/tools/ (parse_dtbo.py / fdt2dts.py, 纯Python无依赖)

## 关键结论

### 面板 (最大硬骨头 → 已塌缩)
- **实际面板 IC: Visionox RM692E5** (`cmdline: msm_drm.dsi_display0=qcom,mdss_dsi_visionox_rm692e5_1080p_dsc_cmd`)
- **mainline 驱动已存在**: `drivers/gpu/drm/panel/panel-visionox-rm692e5.c`
  (CONFIG_DRM_PANEL_VISIONOX_RM692E5, kernel ≥6.6.86, 2025-02 合入, 参考机 Nothing Phone (2a),
   由 linux-mdss-dsi-panel-driver-generator 生成)
- dtbo 里还有 144hz / 非 DSC / r66451 / sharp qhd 等其他 variant (不同板型)
- 关键参数 (从 dtbo overlay 提取, 待精读 entry00):
  - DSC: 8bpp, slice 360x8, 1 slice/pkt
  - reset 序列: 1-10-0-10-1-10 (高10ms-低10ms-高10ms)
  - status 读取: reg 0x0a expect 0x1c, LP mode
  - brightness-max: 0x1fff (13bit)

### 触摸
- **FocalTech (敦泰)** 为主流板型 (19~40 处引用), 次要板型 Goodix
- mainline 无 FocalTech 手机级驱动 → M5 需移植 (MyOS vendor ramdisk/kernel 模块有源码线索)

### dtbo 提取产物
- dtbo.img: DT_TABLE 大端变体 (magic 0xd7b7ab1e), 57 个 overlay, 全部有效 DTB
- 反编译产物: `07_root/mainline/tools/dts/entryXX_*.dts` (58 文件, fdt2dts.py 自研)
- entry00 = 信息最全的主板型 overlay (含 rm692e5 / focaltech / goodix / zte_nolcd)

### 教训记录
1. dtbo.img 头部字段是**大端** (AOSP 标准是 LE) — ZTE 变体
2. vendor_boot.img 的 vendor_dtb 未解 (压缩形态), 需要时用 unpack_bootimg (M4)
3. adb shell 引号链坑: 多段命令一律走脚本文件, 勿直接 su -c "a && b"
4. WSL2 不可用: HCS/E_HYPERV_NOT_INSTALLED → M2 需启用"虚拟机平台"+重启

## 下一步 (M2): 构建环境
- 方案 A (推荐): DISM 启用 VirtualMachinePlatform → 重启 → WSL2 内建交叉工具链
- 方案 B (免重启): GitHub Actions 云构建 (repo 带内核 CI workflow)

#!/bin/bash
# 构建小米12 (cupid) 的 kernel Image 和 boot.img。
#
# 用法（在 WSL/Linux 内运行）：
#   KERNEL_TREE=/root/linux ./tools/build-final.sh
#
# 需要：
#   - 已应用 patches/kernel/ 的内核树（基线见 patches/kernel/base.txt）
#   - 原厂多 DTB 容器（诱饵 DTB）：默认 out/v47-inspect/dtb
#     可用 magiskboot unpack 原厂 boot.img 后取 dtb 字段
#   - aarch64-linux-gnu- 工具链
set -euo pipefail

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO=$(dirname "$HERE")
KERNEL_TREE=${KERNEL_TREE:-/root/linux}
OUT=${OUT:-$REPO/out}
DTS=${DTS:-sm8450-xiaomi-cupid-v-touch}
DECOY_DTB=${DECOY_DTB:-$OUT/v47-inspect/dtb}
IMAGE=${IMAGE:-$OUT/Image-final}
BOOTIMG=${BOOTIMG:-$OUT/boot-final.img}

[ -d "$KERNEL_TREE" ] || { echo "kernel tree not found: $KERNEL_TREE" >&2; exit 1; }
[ -f "$DECOY_DTB" ] || {
    echo "missing decoy DTB: $DECOY_DTB" >&2
    echo "extract it from a stock boot.img (magiskboot unpack -> dtb)" >&2
    exit 1
}
mkdir -p "$OUT"
cd "$KERNEL_TREE"

echo "== config checks =="
grep -q '^CONFIG_CUPID_FORCE_BUILTIN_DTB=y$' .config || {
    echo "CONFIG_CUPID_FORCE_BUILTIN_DTB=y is required" >&2; exit 1; }
grep -q '^# CONFIG_CPU_IDLE is not set$' .config || {
    echo "CONFIG_CPU_IDLE must stay disabled (enabling it blacks out the panel)" >&2; exit 1; }
grep -q '^CONFIG_INITRAMFS_SOURCE=' .config || {
    echo "CONFIG_INITRAMFS_SOURCE is required" >&2; exit 1; }
grep -q "qcom/$DTS.dtb" arch/arm64/boot/dts/qcom/Makefile || {
    echo "dtb-$DTS is not registered in arch/arm64/boot/dts/qcom/Makefile" >&2; exit 1; }

echo "== build DTB ($DTS) =="
export PATH=/usr/lib/ccache:$PATH
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- DTC_FLAGS='-@' "qcom/$DTS.dtb"

echo "== build Image =="
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
     CC='ccache aarch64-linux-gnu-gcc' CUPID_DTB="$DTS" -j"$(nproc)" Image
cp arch/arm64/boot/Image "$IMAGE"

echo "== pack boot.img (header v2, pagesize 2048) =="
python3 "$REPO/tools/mkbootimg/mkbootimg.py" \
    --kernel "$IMAGE" \
    --dtb "$DECOY_DTB" \
    --header_version 2 --pagesize 2048 \
    --base 0x00000000 --kernel_offset 0x10008000 \
    --ramdisk_offset 0x00000000 --tags_offset 0x10000100 \
    --dtb_offset 0x11f00000 \
    --output "$BOOTIMG"

echo "== done =="
sha256sum "$IMAGE" "$BOOTIMG"
echo "boot.img: $BOOTIMG"

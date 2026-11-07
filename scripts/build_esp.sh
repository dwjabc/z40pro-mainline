#!/bin/bash
# 构建可启动 ESP 镜像 (写入 logdump 分区 512MB):
#   \EFI\BOOT\BOOTAA64.EFI = Debian monolithic grubaa64.efi (全模块内嵌)
#   \EFI\BOOT\grub.cfg     = 启动菜单 (linux + devicetree + initrd)
#   \boot\{Image, z40pro.dtb, initramfs.img}
set -euxo pipefail
IMG="$(realpath "$1")"; KERNEL="$(realpath "$2")"; DTB="$(realpath "$3")"; INITRD="$(realpath "$4")"
W="$PWD/espwork"
rm -rf "$W"; mkdir -p "$W/esp/EFI/BOOT" "$W/esp/boot/grub/arm64-efi"

# Debian monolithic grubaa64.efi (全模块内嵌, 单文件可用)
DEB_DIR=http://ports.ubuntu.com/ubuntu-ports/pool/main/g/grub2
DEB=$(curl -s "$DEB_DIR/" | grep -oE 'grub-efi-arm64-bin_[^"]*_arm64\.deb' | tail -1)
[ -n "$DEB" ] || { echo "grub deb not found"; exit 1; }
curl -s -o "$W/grub.deb" "$DEB_DIR/$DEB"
mkdir -p "$W/deb" && dpkg-deb -x "$W/grub.deb" "$W/deb"
GRUB_EFI=$(find "$W/deb" -name 'grubaa64.efi' | head -1)
[ -n "$GRUB_EFI" ] || { echo "grubaa64.efi not found in deb"; exit 1; }
cp "$GRUB_EFI" "$W/esp/EFI/BOOT/BOOTAA64.EFI"

# grub 模块目录 (grub 运行时 insmod 用) 放在 prefix 旁
MODDIR=$(find "$W/deb" -type d -name 'arm64-efi' | head -1)
[ -n "$MODDIR" ] && cp -r "$MODDIR" "$W/esp/EFI/BOOT/arm64-efi"

# grub.cfg: 直接菜单 (grub 启动后 prefix=/EFI/BOOT 可发现同目录 grub.cfg)
cat > "$W/esp/EFI/BOOT/grub.cfg" <<'CFG'
set timeout=3
menuentry "Z40Pro mainline" {
    linux /boot/Image
    devicetree /boot/z40pro.dtb
    initrd /boot/initramfs.img
    boot
}
CFG

# FAT 512MB
dd if=/dev/zero of="$IMG" bs=1M count=512 status=none
mkfs.vfat -F 32 -n Z40PRO "$IMG" >/dev/null
export MTOOLS_SKIP_CHECK=1
mmd -i "$IMG" ::/EFI ::/EFI/BOOT ::/boot
mcopy -i "$IMG" "$W/esp/EFI/BOOT/BOOTAA64.EFI" ::/EFI/BOOT/BOOTAA64.EFI
mcopy -i "$IMG" "$W/esp/EFI/BOOT/grub.cfg" ::/EFI/BOOT/grub.cfg
mcopy -i "$IMG" "$KERNEL" ::/boot/Image
mcopy -i "$IMG" "$DTB" ::/boot/z40pro.dtb
mcopy -i "$IMG" "$INITRD" ::/boot/initramfs.img
[ -d "$MODDIR" ] && mcopy -i "$IMG" -s "$MODDIR" ::/EFI/BOOT/arm64-efi
echo "ESP built: $IMG"

#!/bin/bash
# 构建可启动 ESP 分区镜像 (写入 logdump 分区):
#   FAT: \EFI\BOOT\BOOTAA64.EFI (grub standalone, 内嵌 early cfg)
#        \boot\Image, \boot\z40pro.dtb, \boot\initramfs.img, \boot\grub.cfg
# 用法: build_esp.sh <out_esp.img> <Image> <dtb> <initramfs.img>
set -euxo pipefail
IMG="$(realpath "$1")"; KERNEL="$(realpath "$2")"; DTB="$(realpath "$3")"; INITRD="$(realpath "$4")"
W="$PWD/espwork"
rm -rf "$W"; mkdir -p "$W/memdisk/boot/grub" "$W/esp/EFI/BOOT" "$W/esp/boot/grub"

# early grub 配置 (memdisk 内嵌): 找到含 /boot/Image 的分区设 root, 加载真配置
cat > "$W/memdisk/boot/grub/grub.cfg" <<'CFG'
if search.fs_file /boot/Image; then
    set root=$device
fi
set prefix=($root)/boot/grub
configfile ($root)/boot/grub/grub.cfg
CFG

# 真分区上的菜单
cat > "$W/esp/boot/grub/grub.cfg" <<'CFG'
set timeout=3
menuentry "Z40Pro mainline" {
    linux /boot/Image
    devicetree /boot/z40pro.dtb
    initrd /boot/initramfs.img
    boot
}
CFG

# grub standalone (Debian grub-efi-arm64-bin 提供 grub-mkstandalone)
if ! command -v grub-mkstandalone >/dev/null; then
    apt-get install -y -qq grub-efi-arm64-bin >/dev/null
fi
grub-mkstandalone -O arm64-efi -o "$W/esp/EFI/BOOT/BOOTAA64.EFI" \
    --modules="search_fs_file search_fs_filesearch configfile linux devicetree gzio normal" \
    --install-modules="search_fs_file search_fs_filesearch configfile linux devicetree gzio normal echo sleep test" \
    --locales= --themes= \
    "boot/grub/grub.cfg=$W/memdisk/boot/grub/grub.cfg"

# FAT 512MB (logdump 分区大小)
dd if=/dev/zero of="$IMG" bs=1M count=512 status=none
mkfs.vfat -F 32 -n Z40PRO "$IMG" >/dev/null
export MTOOLS_SKIP_CHECK=1
mmd -i "$IMG" ::/EFI ::/EFI/BOOT ::/boot
mcopy -i "$IMG" "$W/esp/EFI/BOOT/BOOTAA64.EFI" ::/EFI/BOOT/BOOTAA64.EFI
mcopy -i "$IMG" "$W/esp/boot/grub/grub.cfg" ::/boot/grub/grub.cfg
mcopy -i "$IMG" "$KERNEL" ::/boot/Image
mcopy -i "$IMG" "$DTB" ::/boot/z40pro.dtb
mcopy -i "$IMG" "$INITRD" ::/boot/initramfs.img
echo "ESP built: $IMG"

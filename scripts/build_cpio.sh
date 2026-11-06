#!/bin/bash
# CI: 组装 initramfs + boot.img (header v4, 含 dtb) — v2: 绝对路径, 无 cd 依赖
# 用法: build-initramfs.sh <z40pro.dtb> <Image.gz> <out_dir>
set -euxo pipefail
OUT="$(realpath "$1")"
W="$PWD/buildwork"
rm -rf "$W"; mkdir -p "$W/rootfs" "$OUT"
echo "[1/5] busybox"

APK=$(curl -s https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/ \
      | grep -oE 'busybox-static-[0-9][^"]*\.apk' | tail -1)
[ -n "$APK" ] || { echo "busybox apk not found"; exit 1; }
curl -s -o "$W/busybox.apk" "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/$APK"
mkdir -p "$W/apk" && tar -xzf "$W/busybox.apk" -C "$W/apk"
BB=$(find "$W/apk" -name 'busybox*' -type f | head -1)
[ -n "$BB" ] || { echo "busybox binary not found in apk"; find "$W/apk" | head -20; exit 1; }

echo "[2/5] initramfs tree"
R="$W/rootfs"
for d in bin sbin dev proc sys tmp run etc; do mkdir -p "$R/$d"; done
cp initramfs/init "$R/init"
cp "$BB" "$R/bin/busybox"
chmod +x "$R/init" "$R/bin/busybox"
for app in sh mount umount ifconfig ip ls mkdir ln sleep cat echo grep head tail \
           ps setsid cttyhack telnetd mknod sync poweroff reboot dmesg uname; do
  ln -sf busybox "$R/bin/$app"
done

echo "[3/5] cpio"
(cd "$R" && find . | cpio -o -H newc --owner 0:0) | gzip -9 > "$W/initramfs.img"


echo "cpio at $W/initramfs.img"

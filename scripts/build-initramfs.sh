#!/bin/bash
# CI: 组装 initramfs + boot.img (header v4, 含 dtb)
# 用法: build-initramfs.sh <z40pro.dtb> <Image.gz> <out_dir>
set -euo pipefail
DTB="$1"; KERNEL="$2"; OUT="$3"
mkdir -p "$OUT" initramfs-build/root

# ---- arm64 静态 busybox (Alpine busybox-static) ----
echo "-- fetching alpine busybox-static --"
APK=$(curl -s https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/ \
      | grep -oE 'busybox-static-[0-9][^"]*\.apk' | tail -1)
[ -n "$APK" ] || { echo "busybox apk not found"; exit 1; }
curl -s -o busybox.apk "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/aarch64/$APK"
mkdir -p busybox-unpack && tar -xzf busybox.apk -C busybox-unpack
cp busybox-unpack/bin/busybox.static initramfs-build/root/busybox || \
  cp busybox-unpack/usr/bin/busybox initramfs-build/root/busybox
chmod +x initramfs-build/root/busybox

# ---- initramfs 树 ----
cd initramfs-build
mkdir -p root/{bin,sbin,dev,proc,sys,tmp,run,etc}
cp ../initramfs/init root/init
chmod +x root/init
cd root
# busybox 符号链接 (telnetd/sh/ifconfig/mount 等)
for app in sh mount umount ifconfig ip ls mkdir ln sleep cat echo grep head tail \
           ps setsid cttyhack telnetd mknod sync poweroff reboot dmesg uname; do
  ln -sf busybox "bin/$app"
done
# cpio
find . | cpio -o -H newc --owner 0:0 2>/dev/null | gzip -9 > ../initramfs.img
cd ..

# ---- mkbootimg (AOSP, CI 网络可直连) ----
curl -s -o mkbootimg.py "https://raw.githubusercontent.com/aosp-mirror/platform_system_tools/master/mkbootimg/unpack_bootimg.py" 2>/dev/null || true
curl -s -o mkbootimg.py "https://android.googlesource.com/platform/system/tools/mkbootimg/+/refs/heads/main/mkbootimg.py?format=TEXT"
python3 -c "import base64,sys; open('mkbootimg.py','wb').write(base64.b64decode(open('mkbootimg.py','rb').read()))"

python3 mkbootimg.py \
  --header_version 4 \
  --kernel "$KERNEL" \
  --ramdisk initramfs.img \
  --dtb "$DTB" \
  --cmdline "console=ttyMSM0,115200n8 earlycon=qcom_geni,0xa90000 panic=10 rootwait" \
  --pagesize 4096 \
  --output "$OUT/boot.img"

ls -la "$OUT"
echo "=== boot.img built ==="

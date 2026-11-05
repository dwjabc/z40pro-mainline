#!/bin/bash
# Z40 Pro root 通道一键刷写: push boot.img -> dd -> reboot
# 用法: bash flash_and_reboot.sh <boot.img>
# 依赖: adb 在线 + Magisk root; boot_a 节点 /dev/block/by-name/boot_a (sde13)
set -e
ADB="J:\kaifa\手机操作\Z40Pro\01_工具链\platform-tools\adb.exe"
IMG="$1"
[ -f "$IMG" ] || { echo "usage: $0 <boot.img>"; exit 1; }
export MSYS_NO_PATHCONV=1

echo "== push $(basename $IMG) =="
"$ADB" push "$IMG" /data/local/tmp/boot_mainline.img | tail -1

echo "== md5 check =="
PC_MD5=$(md5sum "$IMG" | cut -d' ' -f1)
PH_MD5=$("$ADB" shell "su -c 'md5sum /data/local/tmp/boot_mainline.img'" | cut -d' ' -f1)
echo "pc : $PC_MD5"
echo "ph : $PH_MD5"
[ "$PC_MD5" = "$PH_MD5" ] || { echo "!! md5 mismatch, abort"; exit 1; }

echo "== dd -> boot_a =="
"$ADB" shell "su -c 'dd if=/data/local/tmp/boot_mainline.img of=/dev/block/by-name/boot_a'" | tail -2

echo "== verify partition =="
V_MD5=$("$ADB" shell "su -c 'dd if=/dev/block/by-name/boot_a bs=4M count=256 2>/dev/null | md5sum'" | cut -d' ' -f1)
echo "partition head-96MB md5: $V_MD5"

echo "== reboot =="
"$ADB" reboot
echo "done. 等待重启; PC 侧观察 USB NCM 网卡出现后: 配 192.168.237.1 -> telnet 192.168.237.2"

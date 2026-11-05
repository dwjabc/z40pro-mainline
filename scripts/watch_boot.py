# -*- coding: utf-8 -*-
# 刷写后观察: 轮询 USB 三态 (fastboot / NCM 网卡 / 9008), 输出时间线
# 用法: python -I watch_boot.py [秒数, 默认90]
import subprocess, time, sys

PS = ['powershell', '-NoProfile', '-Command']
FASTBOOT = r'J:\kaifa\手机操作\Z40Pro\01_工具链\platform-tools\fastboot.exe'

def usb_state():
    r = subprocess.run(PS + ["Get-PnpDevice -PresentOnly | ForEach-Object { $_.InstanceId }"],
                       capture_output=True, text=True, timeout=15)
    ids = r.stdout
    state = []
    if 'VID_18D1&PID_D00D' in ids:
        state.append('FASTBOOT')
    if 'VID_05C6&PID_9008' in ids:
        state.append('EDL-9008')
    if 'VID_18D1&PID_4EEE' in ids:
        state.append('NCM-GADGET')
    # NCM host 网卡 (Windows 侧)
    r2 = subprocess.run(PS + ["(Get-NetAdapter | Where-Object { $_.InterfaceDescription -match 'NCM' }).Count"],
                        capture_output=True, text=True, timeout=15)
    if r2.stdout.strip() and int(r2.stdout.strip() or 0) > 0:
        state.append('NCM-NET-UP')
    return state

dur = int(sys.argv[1]) if len(sys.argv) > 1 else 90
t0 = time.time()
last = None
while time.time() - t0 < dur:
    s = '+'.join(usb_state()) or 'USB-SILENT'
    if s != last:
        print(f'[{time.time()-t0:5.1f}s] {s}')
        last = s
    time.sleep(2)
print('观察结束')

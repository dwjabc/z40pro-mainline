# -*- coding: utf-8 -*-
# 扫描 Android 镜像中的 DTB blob (FDT magic 0xd00dfeed) 并按 header totalsize 完整导出
# 用法: python extract_dtb.py <image> <outdir> [prefix]
import struct, os, sys, hashlib

FDT_MAGIC = b'\xd0\x0d\xfe\xed'

def scan(img_path, outdir, prefix):
    data = open(img_path, 'rb').read()
    os.makedirs(outdir, exist_ok=True)
    found, i, n = [], 0, len(data)
    while True:
        i = data.find(FDT_MAGIC, i)
        if i < 0:
            break
        # FDT header: magic, totalsize, off_dt_struct, off_dt_strings, ...
        if i + 40 <= n:
            totalsize = struct.unpack('>I', data[i+4:i+8])[0]
            version = struct.unpack('>I', data[i+20:i+24])[0]
            # 合理性: 大小 4KB~4MB, 版本 16-17, 对齐
            if 4096 <= totalsize <= 4*1024*1024 and version in (16, 17) and totalsize % 4 == 0:
                found.append((i, totalsize, version))
                i += totalsize  # 跳过整个 blob (避免嵌套误报)
                continue
        i += 4
    print(f'{img_path}: {len(found)} DTB candidates')
    seen = set()
    for idx, (off, size, ver) in enumerate(found):
        blob = data[off:off+size]
        h = hashlib.md5(blob).hexdigest()[:8]
        if h in seen:
            print(f'  [skip dup] off=0x{off:x} size={size} md5={h}')
            continue
        seen.add(h)
        out = os.path.join(outdir, f'{prefix}_{idx:02d}_off{off:x}_sz{size}.dtb')
        open(out, 'wb').write(blob)
        print(f'  [dump] off=0x{off:x} size={size} ver={ver} -> {os.path.basename(out)}')

if __name__ == '__main__':
    scan(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'dtb')

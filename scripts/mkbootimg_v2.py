#!/usr/bin/env python3
# 自实现 Android boot image header v2 打包器 (零依赖)
# 布局: header(1 page) -> kernel -> ramdisk -> dtb (各 page 对齐)
import struct, sys, hashlib

def main():
    ap = sys.argv[1:]
    def opt(name):
        return ap[ap.index(name) + 1]
    kernel_f, ramdisk_f, dtb_f = opt('--kernel'), opt('--ramdisk'), opt('--dtb')
    cmdline = opt('--cmdline')
    page_size = int(opt('--pagesize'), 0)
    base = int(opt('--base'), 0)
    k_off = int(opt('--kernel_offset'), 0)
    r_off = int(opt('--ramdisk_offset'), 0)
    tags_off = int(opt('--tags_offset'), 0)
    out = opt('--output')

    kernel = open(kernel_f, 'rb').read()
    ramdisk = open(ramdisk_f, 'rb').read()
    dtb = open(dtb_f, 'rb').read()

    HEADER_SIZE = 1656
    magic = b'ANDROID!'
    name = b''
    main_cmd = cmdline.encode()[:512]
    extra_cmd = b''
    hdr = struct.pack(
        '<8s10I16s512s32s1024sIqIII',    # AOSP v2: recovery_dtbo_offset(q) 紧跟 size(I) 无 pad
                                          # 偏移: size@1632 offset@1636 header_size@1644
                                          #       dt_size@1648 dt_addr@1652 -> 结构总长 1656
        magic,
        len(kernel), base + k_off,
        len(ramdisk), base + r_off,
        0, base + 0x00f00000,            # second_size, second_addr
        base + tags_off,
        page_size,
        2,                                # header_version
        0,                                # os_version
        name,
        main_cmd,
        b'\x00' * 32,                     # id (信息性, ABL 不校验)
        extra_cmd.ljust(1024, b'\x00'),
        0,                                # recovery_dtbo_size
        0,                                # recovery_dtbo_offset
        HEADER_SIZE,
        len(dtb), base + 0x0f000000,      # dt_size, dt_addr
    )
    # struct '<IqI': I(4)+q(8)+I(4)=16 -> 实际偏移: 1632+4=1636 (q 需要 8 对齐?
    # struct 默认无 pad ('<' 不对齐), q 紧跟 I -> 1636..1644, header_size 1644, dt 1652 -> 总 1660 ✓
    assert len(hdr) == HEADER_SIZE, f'header size {len(hdr)} != {HEADER_SIZE}'

    def padded(data):
        pad = (-len(data)) % page_size
        return data + b'\x00' * pad

    # id[0..3] = sha1 截断 (信息性, ABL 不校验); 必须保持 32B 不变长
    sha = hashlib.sha1(kernel + ramdisk).digest()[:16]
    hdr = hdr[:576] + sha.ljust(32, b'\x00') + hdr[608:]

    blob = padded(hdr) + padded(kernel) + padded(ramdisk) + padded(dtb)
    open(out, 'wb').write(blob)
    print(f'boot.img: kernel={len(kernel)} ramdisk={len(ramdisk)} dtb={len(dtb)} total={len(blob)}')

if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
# 解析 Android dtbo.img (DT_TABLE, ZTE magic 变体) 按 entry 表提取全部 overlay DTB
import struct, os, sys, hashlib

def main(img, outdir):
    data = open(img, 'rb').read()
    magic, total_size, header_size, entry_size, entry_count, entries_off, page_size, version = \
        struct.unpack('>8I', data[:32])
    print(f'magic=0x{magic:08x} entries={entry_count} entry_size={entry_size} entries_off={entries_off} ver={version}')
    assert entry_size == 32
    os.makedirs(outdir, exist_ok=True)
    seen = {}
    for i in range(entry_count):
        off = entries_off + i * entry_size
        dt_size, dt_offset, eid, rev = struct.unpack('>4I', data[off:off+16])
        custom = struct.unpack('>4I', data[off+16:off+32])
        blob = data[dt_offset:dt_offset+dt_size]
        ok = blob[:4] == b'\xd0\x0d\xfe\xed'
        h = hashlib.md5(blob).hexdigest()[:8]
        tag = 'DTB' if ok else '???'
        dup = seen.get(h, 0)
        seen[h] = dup + 1
        name = f'entry{i:02d}_id0x{eid:x}_rev0x{rev:x}_{h}' + ('' if not dup else f'_dup{dup}')
        open(os.path.join(outdir, name + '.dtb'), 'wb').write(blob)
        print(f'[{i:02d}] id=0x{eid:x} rev=0x{rev:x} size={dt_size} off=0x{dt_offset:x} {tag} md5={h} custom={custom[0]:#x},{custom[1]:#x}')

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

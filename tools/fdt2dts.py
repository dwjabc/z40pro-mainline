# -*- coding: utf-8 -*-
# 最小 FDT(DTB) -> DTS 反编译器 (纯 Python, 无依赖)  v2: 栈式直接输出
import struct, sys

FDT_BEGIN_NODE, FDT_END_NODE, FDT_PROP, FDT_NOP, FDT_END = 1, 2, 3, 4, 9

def fmt_val(v):
    if len(v) == 0:
        return '<>'
    # 可打印字符串(常见于 compatible/status/panel 名)
    stripped = v.rstrip(b'\x00')
    if v.endswith(b'\x00') and stripped and all(32 <= b < 127 for b in stripped):
        return '"' + stripped.decode() + '"'
    # u32 数组
    if len(v) % 4 == 0:
        words = struct.unpack(f'>{len(v)//4}I', v)
        return '< ' + ' '.join(f'0x{w:08x}' for w in words) + ' >'
    return v.hex(' ')

def main(blob):
    magic, totalsize, off_struct, off_strings, off_rsv, ver, comp, cpuid, sz_strings, sz_struct = \
        struct.unpack('>10I', blob[:40])
    assert magic == 0xd00dfeed, 'not FDT'
    strings = blob[off_strings:off_strings + sz_strings]
    out = ['/dts-v1/;', '']
    stack = []          # (node_name, indent)
    pos = off_struct
    while pos + 4 <= off_struct + sz_struct:
        token = struct.unpack('>I', blob[pos:pos+4])[0]
        pos += 4
        if token == FDT_BEGIN_NODE:
            e = blob.index(b'\x00', pos)
            name = blob[pos:e].decode('utf-8', 'replace')
            pos = (e + 1 + 3) & ~3
            ind = '    ' * len(stack)
            out.append(f'{ind}{name} {{' if name else f'{ind}/ {{')
            stack.append(name)
        elif token == FDT_END_NODE:
            stack.pop()
        elif token == FDT_PROP:
            ln, nameoff = struct.unpack('>2I', blob[pos:pos+8])
            pos += 8
            val = blob[pos:pos+ln]
            pos = (pos + ln + 3) & ~3
            e = strings.index(b'\x00', nameoff)
            pname = strings[nameoff:e].decode('utf-8', 'replace')
            ind = '    ' * len(stack)
            out.append(f'{ind}{pname} = {fmt_val(val)};')
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            break
    while stack:
        stack.pop()
        ind = '    ' * len(stack)
        out.append(f'{ind}}};')
    return '\n'.join(out)

if __name__ == '__main__':
    blob = open(sys.argv[1], 'rb').read()
    print(main(blob))

#!/usr/bin/env python3
# 在内核 qcom Makefile 的 sm8450-samsung-r0q 行后插入 z40pro dtb 条目
import sys

mk = sys.argv[1]
lines = open(mk).read().splitlines(keepends=True)
if any('z40pro' in l for l in lines):
    print('already patched'); sys.exit(0)
for i, l in enumerate(lines):
    if 'sm8450-samsung-r0q.dtb' in l:
        lines.insert(i + 1, 'dtb-$(CONFIG_ARCH_QCOM)\t+= sm8450-nubia-z40pro.dtb\n')
        break
else:
    sys.exit('sm8450-samsung-r0q.dtb not found in Makefile')
open(mk, 'w').write(''.join(lines))
print('Makefile patched OK')

#!/usr/bin/env python3
# 在内核树上应用 Z40 Pro 板级支持:
#  1. dts 拷贝 + qcom Makefile 注册
#  2. Z40PRO_FORCE_BUILTIN_DTB (Kconfig + z40pro_dtb.S + kernel Makefile + setup.c 覆盖 __fdt_pointer)
#  3. Z40PRO_EARLY_FB (z40pro_early.c + z40pro_font.h + kernel Makefile)
# 方案对齐 cupid (Xiaomi 12) 移植的诱饵 DTB 设计
import sys, os, shutil

tree = sys.argv[1]
qcom = os.path.join(tree, 'arch', 'arm64', 'boot', 'dts', 'qcom')
kern = os.path.join(tree, 'arch', 'arm64', 'kernel')
repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DTS = os.path.join(repo, 'kernel-patch', 'arch', 'arm64', 'boot', 'dts', 'qcom',
                       'sm8450-nubia-z40pro.dts')
NF = os.path.join(repo, 'kernel-patch', 'new-files', 'arch', 'arm64', 'kernel')

# --- 1. dts ---
shutil.copy(SRC_DTS, os.path.join(qcom, 'sm8450-nubia-z40pro.dts'))
mk = os.path.join(qcom, 'Makefile')
lines = open(mk).read().splitlines(keepends=True)
if not any('z40pro' in l for l in lines):
    for i, l in enumerate(lines):
        if 'sm8450-samsung-r0q.dtb' in l:
            lines.insert(i + 1, 'dtb-$(CONFIG_ARCH_QCOM)\t+= sm8450-nubia-z40pro.dtb\n')
            break
    else:
        sys.exit('Makefile anchor not found')
    open(mk, 'w').write(''.join(lines))
print('[1] dts + Makefile OK')

# --- 2. Kconfig ---
kc = os.path.join(tree, 'arch', 'arm64', 'Kconfig')
ktxt = open(kc).read()
if 'Z40PRO_FORCE_BUILTIN_DTB' not in ktxt:
    block = (
        'config Z40PRO_FORCE_BUILTIN_DTB\n'
        '\tbool "z40pro: force use of built-in board DTB"\n'
        '\tdefault n\n'
        '\thelp\n'
        '\t  ZTE ABL (NX701J) hands the kernel a vendor DT (cape base + dtbo\n'
        '\t  overlays) and never reads the dt_size/dt_addr fields of the boot\n'
        '\t  image; booting a mainline DT through it is not possible. The boot\n'
        '\t  image carries the stock vendor DTB as a decoy, and setup_arch()\n'
        '\t  replaces the ABL-provided __fdt_pointer with the mainline DTB\n'
        '\t  embedded via arch/arm64/kernel/z40pro_dtb.S.\n'
        '\n'
        'config Z40PRO_EARLY_FB\n'
        '\tbool "z40pro: early framebuffer console (draw log on ABL splash)"\n'
        '\tdefault n\n'
        '\thelp\n'
        '\t  Draw kernel messages onto the framebuffer left scanning by the\n'
        '\t  bootloader, from early_initcall. Enable with cmdline\n'
        '\t  z40pro.fb=0x<phys>,<stride_px>,<height>,<width>,<bpp>.\n'
        '\n'
    )
    anchor = 'config ARM64_WORKAROUND_CLEAN_CACHE\n'
    assert anchor in ktxt, 'Kconfig anchor missing'
    ktxt = ktxt.replace(anchor, block + anchor, 1)
    open(kc, 'w').write(ktxt)
print('[2] Kconfig OK')

# --- 3. z40pro_dtb.S + early fb 文件 ---
src = (
    '/* SPDX-License-Identifier: GPL-2.0 */\n'
    '/* z40pro (NX701J): embed the mainline board DTB into the kernel image.\n'
    ' * With CONFIG_Z40PRO_FORCE_BUILTIN_DTB, setup_arch() replaces the DTB\n'
    ' * pointer handed over by ZTE ABL with this embedded mainline DTB\n'
    ' * (decoy scheme, ported from the Xiaomi 12/13 cupid/fuxi ports). */\n'
    '\t.section .rodata, "a"\n'
    '\t.balign\t8\n'
    '\t.globl\tz40pro_dtb\n'
    'z40pro_dtb:\n'
    '\t.incbin\tZ40PRO_DTB_FILE\n'
    '\t.globl\tz40pro_dtb_end\n'
    'z40pro_dtb_end:\n'
)
open(os.path.join(kern, 'z40pro_dtb.S'), 'w', newline='\n').write(src)
for fn in ('z40pro_early.c', 'z40pro_font.h'):
    shutil.copy(os.path.join(NF, fn), os.path.join(kern, fn))
print('[3] z40pro_dtb.S + early fb files OK')

# --- 4. kernel Makefile ---
km = os.path.join(kern, 'Makefile')
ktxt = open(km).read()
if 'z40pro_dtb.o' not in ktxt:
    ktxt += (
        '\nobj-$(CONFIG_Z40PRO_FORCE_BUILTIN_DTB) += z40pro_dtb.o\n'
        'obj-$(CONFIG_Z40PRO_EARLY_FB) += z40pro_early.o\n'
        'Z40PRO_DTB ?= sm8450-nubia-z40pro\n'
        'AFLAGS_z40pro_dtb.o += -DZ40PRO_DTB_FILE=\'"arch/arm64/boot/dts/qcom/$(Z40PRO_DTB).dtb"\'\n'
        '$(obj)/z40pro_dtb.o: arch/arm64/boot/dts/qcom/$(Z40PRO_DTB).dtb\n')
    open(km, 'w').write(ktxt)
print('[4] kernel Makefile OK')

# --- 5. setup.c ---
sc = os.path.join(kern, 'setup.c')
stxt = open(sc).read()
if 'Z40PRO_FORCE_BUILTIN_DTB' not in stxt:
    anchor = '\tearly_fixmap_init();\n\tearly_ioremap_init();\n'
    assert anchor in stxt, 'setup.c anchor missing'
    ins = (
        anchor + '\n'
        '\t/*\n'
        '\t * z40pro: ZTE ABL hands the kernel a vendor DT (cape base + dtbo\n'
        '\t * overlays) and never reads the dt fields of the boot image. The\n'
        '\t * boot image carries the stock vendor DTB as a decoy; swap in the\n'
        '\t * mainline DTB compiled into the kernel (z40pro_dtb.S).\n'
        '\t */\n'
        '#if IS_ENABLED(CONFIG_Z40PRO_FORCE_BUILTIN_DTB)\n'
        '\t{\n'
        '\t\textern const unsigned char z40pro_dtb[];\n'
        '\t\t__fdt_pointer = __pa_symbol((unsigned long)z40pro_dtb);\n'
        '\t}\n'
        '#endif\n')
    stxt = stxt.replace(anchor, ins, 1)
    open(sc, 'w').write(stxt)
print('[5] setup.c OK')
print('board applied fully')

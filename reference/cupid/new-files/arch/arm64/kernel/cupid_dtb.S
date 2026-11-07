/* SPDX-License-Identifier: GPL-2.0 */
/*
 * cupid (Xiaomi 12): embed the mainline board DTB into the kernel image.
 * With CONFIG_CUPID_FORCE_BUILTIN_DTB, setup_arch() replaces the DTB pointer
 * handed over by ABL with this embedded one, so the kernel never sees the
 * vendor DTB that ABL validated/overlaid (the boot image still carries the
 * stock vendor blob purely as a decoy for ABL).
 * Build order: make qcom/$(CUPID_DTB).dtb first, then make Image.
 * Ported from the Xiaomi 13 (fuxi) mainline port (fuxi_dtb.S).
 */
	.section .rodata, "a"
	.balign	8
	.globl	cupid_dtb
cupid_dtb:
	.incbin	CUPID_DTB_FILE
	.globl	cupid_dtb_end
cupid_dtb_end:

// SPDX-License-Identifier: GPL-2.0
/*
 * cupid??iaomi 13????????console??impledrm/fbcon ??????????????????
 * bootloader ??????????????????????UART?????? simpledrm probe ?????????
 * ????????????????????
 *
 * ????????? z40pro.fb=0x<phys>,<stride_px>,<height>,<width>,<bpp> ???????
 * early_initcall ?????ON_PRINTBUFFER ??????????????????DT ????????
 * simple-framebuffer ???late_initcall_sync ???????????? fbcon??
 */
#include <linux/console.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/kernel.h>
#include <linux/of.h>
#include <asm/cacheflush.h>

#include "z40pro_font.h"

#define z40pro_TEXT_X	16
#define z40pro_TEXT_Y	64
#define z40pro_TEXT_SCALE	3
#define z40pro_TEXT_LH	50
#define z40pro_TEXT_MAX	48

static phys_addr_t z40pro_fb_base;
static unsigned int z40pro_fb_stride, z40pro_fb_width, z40pro_fb_height;
static bool z40pro_fb_valid, z40pro_cons_registered;
static void *z40pro_fb_lin;
static unsigned int cupid_text_line;
static char z40pro_cons_buf[z40pro_TEXT_MAX];
static unsigned int z40pro_cons_len;

static int __init z40pro_fb_param(char *str)
{
	unsigned long long base;
	unsigned int stride, height, width, bpp;

	if (str && sscanf(str, "0x%llx,%u,%u,%u,%u",
			  &base, &stride, &height, &width, &bpp) == 5 &&
	    stride && height && width && bpp == 32) {
		z40pro_fb_base = base;
		z40pro_fb_stride = stride;
		z40pro_fb_width = width;
		z40pro_fb_height = height;
		z40pro_fb_valid = true;
	}
	return 0;
}
early_param("z40pro.fb", z40pro_fb_param);

/* ?????????8x16 ?????? z40pro_TEXT_SCALE ???????????????????????*/
static void z40pro_draw_line(const char *s, unsigned int len)
{
	unsigned int maxc = (z40pro_fb_width - z40pro_TEXT_X) / (8 * z40pro_TEXT_SCALE);
	unsigned int row, sy, ch, col, sc, x, y;

	len = min3(len, maxc, (unsigned int)z40pro_TEXT_MAX);
	y = z40pro_TEXT_Y + cupid_text_line * z40pro_TEXT_LH;
	if (y + z40pro_TEXT_LH > z40pro_fb_height) {
		cupid_text_line = 0;
		y = z40pro_TEXT_Y;
	}
	for (row = 0; row < 16; row++) {
		for (sy = 0; sy < z40pro_TEXT_SCALE; sy++) {
			u32 *p = (u32 *)z40pro_fb_lin +
				 (phys_addr_t)(y + row * z40pro_TEXT_SCALE + sy) *
				 z40pro_fb_stride + z40pro_TEXT_X;

			/* ???????????????????*/
			for (x = 0; x < z40pro_fb_width - z40pro_TEXT_X; x++)
				p[x] = 0;
			for (ch = 0; ch < len; ch++) {
				unsigned char c = s[ch];
				unsigned char bits;

				if (c < 32 || c > 126)
					c = ' ';
				bits = cupid_font8x16[c - 32][row];
				for (col = 0; col < 8; col++) {
					u32 color = (bits & (0x80u >> col)) ? 0x00ffffffu : 0;

					for (sc = 0; sc < z40pro_TEXT_SCALE; sc++)
						p[(ch * 8 + col) * z40pro_TEXT_SCALE + sc] = color;
				}
			}
			dcache_clean_poc((unsigned long)p,
					 (unsigned long)(p + z40pro_fb_width - z40pro_TEXT_X));
		}
	}
	cupid_text_line++;
}

static void z40pro_console_write(struct console *co, const char *s,
			       unsigned int count)
{
	unsigned int i;

	for (i = 0; i < count; i++) {
		if (s[i] == '\r')
			continue;
		if (s[i] == '\n' || z40pro_cons_len >= z40pro_TEXT_MAX) {
			z40pro_draw_line(z40pro_cons_buf, z40pro_cons_len);
			z40pro_cons_len = 0;
			if (s[i] == '\n')
				continue;
		}
		z40pro_cons_buf[z40pro_cons_len++] = s[i];
	}
}

static struct console z40pro_console = {
	.name	= "cupidfb",
	.write	= z40pro_console_write,
	.flags	= CON_PRINTBUFFER | CON_ENABLED,
	.index	= -1,
};

static int __init z40pro_console_init(void)
{
	size_t size = (size_t)z40pro_fb_stride * z40pro_fb_height * 4;
	unsigned int y;

	if (!z40pro_fb_valid)
		return 0;
	/*
	 * ?????? linear map ??? arm64 ioremap() ???????????linear map + dcache clean??
	 * DTS ????????no-map??ont_splash?????? linear map ?????ioremap_wc??
	 */
	if (pfn_is_map_memory(PHYS_PFN(z40pro_fb_base)))
		z40pro_fb_lin = phys_to_virt(z40pro_fb_base);
	else
		z40pro_fb_lin = (void __force *)ioremap_wc(z40pro_fb_base, size);
	if (!z40pro_fb_lin)
		return -ENOMEM;
	for (y = 0; y < z40pro_fb_height; y++) {
		u32 *p = (u32 *)z40pro_fb_lin + (phys_addr_t)y * z40pro_fb_stride;

		memset(p, 0, z40pro_fb_width * 4);
		dcache_clean_poc((unsigned long)p, (unsigned long)(p + z40pro_fb_width));
	}
	z40pro_cons_registered = true;
	register_console(&z40pro_console);
	return 0;
}
early_initcall(z40pro_console_init);

/* simpledrm + fbcon ?????????????????????????????? */
static int __init z40pro_console_handover(void)
{
	/* CUPID_KEEP_CONSOLE: debug - never hand over, keep early console alive */
	return 0;
	struct device_node *np = of_find_compatible_node(NULL, NULL, "simple-framebuffer");
	bool fb = np && of_device_is_available(np);

	of_node_put(np);
	if (z40pro_cons_registered && fb) {
		pr_info("cupid: handing screen over to simpledrm/fbcon\n");
		unregister_console(&z40pro_console);
		z40pro_cons_registered = false;
	}
	return 0;
}
late_initcall_sync(z40pro_console_handover);



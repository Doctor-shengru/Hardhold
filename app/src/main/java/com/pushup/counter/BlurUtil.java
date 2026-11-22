package com.pushup.counter;

import android.graphics.Bitmap;

/** 小图三重箱式模糊（近似高斯），用于玻璃背景，跨版本可用、耗时可忽略。 */
public final class BlurUtil {

    private BlurUtil() {}

    public static Bitmap blur(Bitmap src, int radius) {
        if (src == null || radius <= 0) return src;
        int w = src.getWidth(), h = src.getHeight();
        if (w <= 1 || h <= 1) return src;
        int[] pixels = new int[w * h];
        src.getPixels(pixels, 0, w, 0, 0, w, h);
        for (int pass = 0; pass < 3; pass++) {
            boxBlurHorizontal(pixels, w, h, radius);
            boxBlurVertical(pixels, w, h, radius);
        }
        Bitmap out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        out.setPixels(pixels, 0, w, 0, 0, w, h);
        return out;
    }

    private static void boxBlurHorizontal(int[] px, int w, int h, int r) {
        int[] line = new int[w];
        float div = 2 * r + 1;
        for (int y = 0; y < h; y++) {
            int base = y * w;
            int a = 0, rr = 0, g = 0, b = 0;
            for (int i = -r; i <= r; i++) {
                int p = px[base + clamp(i, 0, w - 1)];
                a += (p >>> 24) & 0xFF; rr += (p >> 16) & 0xFF; g += (p >> 8) & 0xFF; b += p & 0xFF;
            }
            for (int x = 0; x < w; x++) {
                line[x] = ((int) (a / div) << 24) | ((int) (rr / div) << 16) | ((int) (g / div) << 8) | (int) (b / div);
                int outP = px[base + clamp(x - r, 0, w - 1)];
                int inP = px[base + clamp(x + r + 1, 0, w - 1)];
                a += ((inP >>> 24) & 0xFF) - ((outP >>> 24) & 0xFF);
                rr += ((inP >> 16) & 0xFF) - ((outP >> 16) & 0xFF);
                g += ((inP >> 8) & 0xFF) - ((outP >> 8) & 0xFF);
                b += (inP & 0xFF) - (outP & 0xFF);
            }
            System.arraycopy(line, 0, px, base, w);
        }
    }

    private static void boxBlurVertical(int[] px, int w, int h, int r) {
        int[] col = new int[h];
        float div = 2 * r + 1;
        for (int x = 0; x < w; x++) {
            int a = 0, rr = 0, g = 0, b = 0;
            for (int i = -r; i <= r; i++) {
                int p = px[clamp(i, 0, h - 1) * w + x];
                a += (p >>> 24) & 0xFF; rr += (p >> 16) & 0xFF; g += (p >> 8) & 0xFF; b += p & 0xFF;
            }
            for (int y = 0; y < h; y++) {
                col[y] = ((int) (a / div) << 24) | ((int) (rr / div) << 16) | ((int) (g / div) << 8) | (int) (b / div);
                int outP = px[clamp(y - r, 0, h - 1) * w + x];
                int inP = px[clamp(y + r + 1, 0, h - 1) * w + x];
                a += ((inP >>> 24) & 0xFF) - ((outP >>> 24) & 0xFF);
                rr += ((inP >> 16) & 0xFF) - ((outP >> 16) & 0xFF);
                g += ((inP >> 8) & 0xFF) - ((outP >> 8) & 0xFF);
                b += (inP & 0xFF) - (outP & 0xFF);
            }
            for (int y = 0; y < h; y++) px[y * w + x] = col[y];
        }
    }

    private static int clamp(int v, int lo, int hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }
}

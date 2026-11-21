package com.pushup.counter;

import android.graphics.Bitmap;
import android.graphics.Matrix;
import android.media.Image;

import java.nio.ByteBuffer;

/** 相机 YUV_420_888 转 Bitmap，并按需旋转/镜像。 */
public final class YuvConverter {

    private YuvConverter() {}

    public static Bitmap toUprightBitmap(Image image, int rotationDegrees, boolean mirror) {
        int w = image.getWidth();
        int h = image.getHeight();
        int[] argb = toArgb(image, w, h);
        Bitmap raw = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888);
        raw.setPixels(argb, 0, w, 0, 0, w, h);

        if (rotationDegrees == 0 && !mirror) return raw;

        Matrix m = new Matrix();
        m.postRotate(rotationDegrees);
        if (mirror) m.postScale(-1f, 1f);
        Bitmap out = Bitmap.createBitmap(raw, 0, 0, w, h, m, true);
        if (out != raw) raw.recycle();
        return out;
    }

    private static int[] toArgb(Image image, int w, int h) {
        Image.Plane[] planes = image.getPlanes();
        ByteBuffer yBuf = planes[0].getBuffer();
        ByteBuffer uBuf = planes[1].getBuffer();
        ByteBuffer vBuf = planes[2].getBuffer();
        int yRow = planes[0].getRowStride();
        int yPix = planes[0].getPixelStride();
        int uRow = planes[1].getRowStride();
        int uPix = planes[1].getPixelStride();
        int vRow = planes[2].getRowStride();
        int vPix = planes[2].getPixelStride();

        int[] out = new int[w * h];
        for (int y = 0; y < h; y++) {
            int yOff = y * yRow;
            int uvRow = y >> 1;
            for (int x = 0; x < w; x++) {
                int yy = yBuf.get(yOff + x * yPix) & 0xFF;
                int ux = x >> 1;
                int u = (uBuf.get(uvRow * uRow + ux * uPix) & 0xFF) - 128;
                int v = (vBuf.get(uvRow * vRow + ux * vPix) & 0xFF) - 128;
                int r = yy + (int) (1.402f * v);
                int g = yy - (int) (0.344136f * u + 0.714136f * v);
                int b = yy + (int) (1.772f * u);
                out[y * w + x] = 0xFF000000 | (clamp(r) << 16) | (clamp(g) << 8) | clamp(b);
            }
        }
        return out;
    }

    private static int clamp(int v) {
        return v < 0 ? 0 : (v > 255 ? 255 : v);
    }
}

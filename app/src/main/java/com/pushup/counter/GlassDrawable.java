package com.pushup.counter;

import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;

/**
 * 轻玻璃背景：半透明深色底 + 顶部柔光 + 1px 受光边。
 * 画在相机预览上时读作「深色磨砂玻璃」，不依赖 RenderEffect，老机型也不掉帧。
 */
public final class GlassDrawable extends Drawable {

    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint highlight = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint border = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF rect = new RectF();
    private final float density;
    private float radius;
    private boolean shaderBuilt;
    private int lastHeight = -1;

    public GlassDrawable(float density, float radiusDp) {
        this.density = density;
        this.radius = radiusDp * density;
    }

    public void setRadiusDp(float radiusDp) {
        this.radius = radiusDp * density;
        invalidateSelf();
    }

    @Override
    protected void onBoundsChange(android.graphics.Rect bounds) {
        super.onBoundsChange(bounds);
        shaderBuilt = false;
    }

    @Override
    public void draw(Canvas canvas) {
        android.graphics.Rect b = getBounds();
        if (b.width() <= 0 || b.height() <= 0) return;
        float r = Math.min(radius, Math.min(b.width(), b.height()) / 2f);
        rect.set(b);

        // 底：深色半透明，透出后面的相机画面
        fill.setColor(0xC8121519);
        canvas.drawRoundRect(rect, r, r, fill);

        // 顶部柔光（模拟玻璃受光）
        if (!shaderBuilt || lastHeight != b.height()) {
            highlight.setShader(new LinearGradient(
                    0, b.top, 0, b.top + b.height() * 0.55f,
                    0x1FFFFFFF, 0x00FFFFFF, Shader.TileMode.CLAMP));
            shaderBuilt = true;
            lastHeight = b.height();
        }
        canvas.drawRoundRect(rect, r, r, highlight);

        // 1px 受光边
        border.setStyle(Paint.Style.STROKE);
        border.setStrokeWidth(Math.max(1f, density));
        border.setColor(0x3DFFFFFF);
        canvas.drawRoundRect(rect, r, r, border);
        border.setStyle(Paint.Style.FILL);
    }

    @Override
    public void setAlpha(int alpha) {}

    @Override
    public void setColorFilter(android.graphics.ColorFilter colorFilter) {}

    @Override
    public int getOpacity() {
        return android.graphics.PixelFormat.TRANSLUCENT;
    }

    /** 供在自绘 View 里复用同一套玻璃外观 */
    public static void paintGlass(Canvas canvas, RectF r, float corner, float density, Paint work) {
        work.setStyle(Paint.Style.FILL);
        work.setColor(0xC8121519);
        canvas.drawRoundRect(r, corner, corner, work);

        work.setShader(new LinearGradient(0, r.top, 0, r.top + r.height() * 0.55f,
                0x1FFFFFFF, 0x00FFFFFF, Shader.TileMode.CLAMP));
        canvas.drawRoundRect(r, corner, corner, work);
        work.setShader(null);

        work.setStyle(Paint.Style.STROKE);
        work.setStrokeWidth(Math.max(1f, density));
        work.setColor(0x3DFFFFFF);
        canvas.drawRoundRect(r, corner, corner, work);
        work.setStyle(Paint.Style.FILL);
    }
}

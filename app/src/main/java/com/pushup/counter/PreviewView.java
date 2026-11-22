package com.pushup.counter;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.media.Image;
import android.view.View;

/** 把相机画面、骨架和计数信息画在同一个 View 上，保证坐标严格对齐。 */
public final class PreviewView extends View {

    private Bitmap frame;
    private float[] pose;          // 33 * 3: x, y, visibility（归一化坐标）
    private int count;
    private PushupCounter.State state = PushupCounter.State.NO_POSE;
    private float angle = Float.NaN;
    private float fps;
    private boolean poseValid;
    private int topInset = 0;

    public void setTopInset(int px) {
        this.topInset = px;
        invalidate();
    }

    private final Paint bitmapPaint = new Paint(Paint.FILTER_BITMAP_FLAG);
    private final Paint bonePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint jointPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint textPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint subPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF dest = new RectF();
    private final RectF pill = new RectF();
    private final Paint glassPaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    /** 骨架连线：肩肘腕、肩髋、髋膝踝 */
    private static final int[][] BONES = {
            {11, 13}, {13, 15}, {12, 14}, {14, 16},
            {11, 12}, {11, 23}, {12, 24}, {23, 24},
            {23, 25}, {25, 27}, {24, 26}, {26, 28},
            {27, 29}, {28, 30}
    };

    public PreviewView(android.content.Context ctx) {
        super(ctx);
        bonePaint.setStyle(Paint.Style.STROKE);
        bonePaint.setStrokeWidth(dp(4));
        bonePaint.setColor(0xFF66E08A);
        jointPaint.setStyle(Paint.Style.FILL);
        jointPaint.setColor(Color.WHITE);

        textPaint.setColor(Color.WHITE);
        textPaint.setTextAlign(Paint.Align.CENTER);
        textPaint.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
        textPaint.setShadowLayer(dp(8), 0, dp(2), 0xCC000000);

        subPaint.setColor(0xFFE0E0E0);
        subPaint.setTextAlign(Paint.Align.LEFT);
        subPaint.setShadowLayer(dp(6), 0, dp(2), 0xCC000000);
    }

    private float dp(float v) {
        return v * getResources().getDisplayMetrics().density;
    }

    private float sp(float v) {
        return v * getResources().getDisplayMetrics().scaledDensity;
    }

    public void setFrame(Bitmap bmp) {
        // 不主动 recycle：MediaPipe 可能仍在引用上一帧，交给 GC 回收更安全
        frame = bmp;
        invalidate();
    }

    public void setPose(float[] pose, boolean valid) {
        this.pose = pose;
        this.poseValid = valid;
        invalidate();
    }

    public void setStats(int count, PushupCounter.State state, float angle, float fps) {
        this.count = count;
        this.state = state;
        this.angle = angle;
        this.fps = fps;
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        canvas.drawColor(Color.BLACK);

        float vw = getWidth(), vh = getHeight();
        if (frame != null && !frame.isRecycled() && frame.getWidth() > 0) {
            float scale = Math.min(vw / frame.getWidth(), vh / frame.getHeight());
            float dw = frame.getWidth() * scale, dh = frame.getHeight() * scale;
            dest.set((vw - dw) / 2f, (vh - dh) / 2f, (vw + dw) / 2f, (vh + dh) / 2f);
            canvas.drawBitmap(frame, null, dest, bitmapPaint);
            drawSkeleton(canvas);
        } else {
            dest.set(0, 0, vw, vh);
        }
        drawHud(canvas, vw, vh);
    }

    private void drawSkeleton(Canvas canvas) {
        if (!poseValid || pose == null) return;
        for (int[] bone : BONES) {
            int a = bone[0], b = bone[1];
            if (pose[a * 3 + 2] < 0.3f || pose[b * 3 + 2] < 0.3f) continue;
            canvas.drawLine(
                    dest.left + pose[a * 3] * dest.width(),
                    dest.top + pose[a * 3 + 1] * dest.height(),
                    dest.left + pose[b * 3] * dest.width(),
                    dest.top + pose[b * 3 + 1] * dest.height(),
                    bonePaint);
        }
        for (int i = 0; i < 33; i++) {
            if (pose[i * 3 + 2] < 0.3f) continue;
            canvas.drawCircle(
                    dest.left + pose[i * 3] * dest.width(),
                    dest.top + pose[i * 3 + 1] * dest.height(),
                    dp(3.5f), jointPaint);
        }
    }

    private void drawHud(Canvas canvas, float vw, float vh) {
        textPaint.setTextSize(sp(84));
        String countText = String.valueOf(count);
        float tw = textPaint.measureText(countText);
        float padH = dp(30), padV = dp(16);
        pill.set(vw / 2f - tw / 2f - padH, topInset + dp(12),
                vw / 2f + tw / 2f + padH, topInset + dp(12) + sp(84) + padV * 2);
        GlassDrawable.paintGlass(canvas, pill, dp(26),
                getResources().getDisplayMetrics().density, glassPaint);
        canvas.drawText(countText, vw / 2f, pill.bottom - padV * 1.35f, textPaint);

        textPaint.setTextSize(sp(17));
        String label;
        switch (state) {
            case UP: label = "撑起"; break;
            case DOWN: label = "下落"; break;
            case MIDDLE: label = "动作中"; break;
            default: label = "未检测到人"; break;
        }
        canvas.drawText(label, vw / 2f, pill.bottom + sp(22), textPaint);

        subPaint.setTextSize(sp(13));
        String detail = "肘角 " + (Float.isNaN(angle) ? "--" : String.valueOf(Math.round(angle))) + "°"
                + "    " + String.format("%.0f", fps) + " fps";
        canvas.drawText(detail, dp(16), vh - dp(20), subPaint);

        if (!poseValid) {
            subPaint.setTextSize(sp(15));
            subPaint.setTextAlign(Paint.Align.CENTER);
            subPaint.setColor(0xFFFFD666);
            canvas.drawText("把手机放稳，让全身进入画面", vw / 2f, vh - dp(64), subPaint);
            subPaint.setTextAlign(Paint.Align.LEFT);
            subPaint.setColor(0xFFE0E0E0);
        }
    }
}

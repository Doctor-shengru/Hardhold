package com.pushup.counter;

/**
 * 俯卧撑计数状态机。纯 Java，不依赖 Android，便于离线单元测试。
 *
 * 用肘部角度（肩-肘-腕）作为动作信号：
 *   - 平滑后角度 >= upAngle   视为「撑起」
 *   - 平滑后角度 <= downAngle 视为「下落」
 *   - 中间区域保持原状态（滞回，抗抖动）
 * 只有完整经历「撑起 -> 下落 -> 撑起」才计一次，
 * 且状态切换需要连续 CONFIRM_FRAMES 帧确认 + 最短间隔，防止手抖乱计数。
 */
public final class PushupCounter {

    public enum State { NO_POSE, UP, DOWN, MIDDLE }

    public static final float DEFAULT_UP_ANGLE = 158f;
    public static final float DEFAULT_DOWN_ANGLE = 95f;

    /** 角度低于该值认为关节不可见，本帧不参与判断 */
    public static final float MIN_VISIBILITY = 0.4f;
    /** 无姿态持续这么久就清零当前状态（人离开画面） */
    private static final long LOST_MS = 1500L;
    /** 两次状态切换的最短间隔 */
    private static final long MIN_SWITCH_MS = 100L;
    /** 需要连续多少帧一致才切换状态 */
    private static final int CONFIRM_FRAMES = 2;
    /** 角度平滑系数（越大越跟手、越少平滑） */
    private static final float SMOOTH = 0.45f;

    private float upAngle = DEFAULT_UP_ANGLE;
    private float downAngle = DEFAULT_DOWN_ANGLE;

    private State state = State.NO_POSE;
    private State candidate = State.NO_POSE;
    private int confirmFrames;
    private int count;
    private float smoothed = Float.NaN;
    private long lastSwitchMs;
    private long lastPoseMs;
    private boolean wentDown;

    /** 喂入一帧角度。visibility 低于阈值或 angle 为 NaN 表示本帧没有人。 */
    public synchronized void feed(float angleDeg, float visibility, long nowMs) {
        if (Float.isNaN(angleDeg) || visibility < MIN_VISIBILITY) {
            if (state != State.NO_POSE && nowMs - lastPoseMs > LOST_MS) {
                state = State.NO_POSE;
                candidate = State.NO_POSE;
                confirmFrames = 0;
                smoothed = Float.NaN;
                wentDown = false;
            }
            return;
        }
        lastPoseMs = nowMs;
        smoothed = Float.isNaN(smoothed) ? angleDeg : smoothed + (angleDeg - smoothed) * SMOOTH;

        State desired;
        if (smoothed >= upAngle) desired = State.UP;
        else if (smoothed <= downAngle) desired = State.DOWN;
        else desired = State.MIDDLE;

        if (desired == state) {
            candidate = state;
            confirmFrames = 0;
            return;
        }
        if (desired == candidate) {
            confirmFrames++;
        } else {
            candidate = desired;
            confirmFrames = 1;
        }
        if (confirmFrames < CONFIRM_FRAMES || nowMs - lastSwitchMs < MIN_SWITCH_MS) return;

        if (desired == State.DOWN) {
            wentDown = true;
        } else if (desired == State.UP && wentDown) {
            count++;
            wentDown = false;
        }
        state = desired;
        lastSwitchMs = nowMs;
        confirmFrames = 0;
    }

    public synchronized int count() { return count; }

    public synchronized State state() { return state; }

    /** 平滑后的肘角；当前无人时返回 NaN */
    public synchronized float angle() { return smoothed; }

    public synchronized boolean hasPose(long nowMs) { return nowMs - lastPoseMs <= LOST_MS; }

    public synchronized void reset() {
        count = 0;
        state = State.NO_POSE;
        candidate = State.NO_POSE;
        confirmFrames = 0;
        smoothed = Float.NaN;
        wentDown = false;
    }

    public synchronized void setAngles(float up, float down) {
        if (down > 0 && up > down) {
            this.downAngle = down;
            this.upAngle = up;
        }
    }

    public synchronized float upAngle() { return upAngle; }

    public synchronized float downAngle() { return downAngle; }
}

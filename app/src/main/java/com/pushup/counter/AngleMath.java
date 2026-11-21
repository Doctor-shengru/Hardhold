package com.pushup.counter;

/** 关键点角度计算，纯 Java，无 Android 依赖。 */
public final class AngleMath {

    private AngleMath() {}

    /** 计算 a-b-c 在 b 点的夹角（度）。任一点重合时返回 NaN。 */
    public static float angleAt(float ax, float ay, float az,
                                float bx, float by, float bz,
                                float cx, float cy, float cz) {
        float v1x = ax - bx, v1y = ay - by, v1z = az - bz;
        float v2x = cx - bx, v2y = cy - by, v2z = cz - bz;
        float n1 = (float) Math.sqrt(v1x * v1x + v1y * v1y + v1z * v1z);
        float n2 = (float) Math.sqrt(v2x * v2x + v2y * v2y + v2z * v2z);
        if (n1 < 1e-6f || n2 < 1e-6f) return Float.NaN;
        float cos = (v1x * v2x + v1y * v2y + v1z * v2z) / (n1 * n2);
        if (cos > 1f) cos = 1f;
        if (cos < -1f) cos = -1f;
        return (float) Math.toDegrees(Math.acos(cos));
    }
}

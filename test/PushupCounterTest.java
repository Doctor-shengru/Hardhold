import com.pushup.counter.PushupCounter;
import com.pushup.counter.AngleMath;

/** 纯桌面 JVM 单测：不依赖 Android，直接 java 运行。 */
public class PushupCounterTest {

    private static int passed = 0, failed = 0;

    public static void main(String[] args) {
        testSingleRep();
        testTwoReps();
        testJitterNoCount();
        testHalfRepNotCounted();
        testNoPoseIgnored();
        testReset();
        testAngleMath();
        testLostPoseResetsState();
        System.out.println();
        System.out.println("PASS " + passed + "  FAIL " + failed);
        if (failed > 0) System.exit(1);
    }

    /** 模拟一段动作：从 start 匀速到 end，每帧 33ms */
    private static long ramp(PushupCounter c, float start, float end, int frames, long t) {
        for (int i = 1; i <= frames; i++) {
            float a = start + (end - start) * i / frames;
            c.feed(a, 0.9f, t);
            t += 33;
        }
        return t;
    }

    private static long hold(PushupCounter c, float a, int frames, long t) {
        for (int i = 0; i < frames; i++) {
            c.feed(a, 0.9f, t);
            t += 33;
        }
        return t;
    }

    private static void testSingleRep() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        t = hold(c, 172, 10, t);
        t = ramp(c, 172, 62, 20, t);
        t = hold(c, 62, 8, t);
        t = ramp(c, 62, 172, 20, t);
        t = hold(c, 172, 10, t);
        check("single rep", c.count() == 1, "count=" + c.count());
    }

    private static void testTwoReps() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        for (int r = 0; r < 2; r++) {
            t = hold(c, 172, 8, t);
            t = ramp(c, 172, 62, 20, t);
            t = hold(c, 62, 8, t);
            t = ramp(c, 62, 172, 20, t);
        }
        t = hold(c, 172, 8, t);
        check("two reps", c.count() == 2, "count=" + c.count());
    }

    private static void testJitterNoCount() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        float[] noise = {168, 172, 165, 174, 170, 160, 175, 166, 171, 169};
        for (int i = 0; i < 100; i++) {
            c.feed(noise[i % noise.length], 0.9f, t);
            t += 33;
        }
        check("jitter at top no count", c.count() == 0, "count=" + c.count());
    }

    private static void testHalfRepNotCounted() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        t = hold(c, 172, 10, t);
        t = ramp(c, 172, 120, 15, t);   // 只到一半
        t = hold(c, 120, 8, t);
        t = ramp(c, 120, 172, 15, t);
        t = hold(c, 172, 10, t);
        check("half rep not counted", c.count() == 0, "count=" + c.count());
    }

    private static void testNoPoseIgnored() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        for (int i = 0; i < 30; i++) {
            c.feed(Float.NaN, 0f, t);
            t += 33;
        }
        check("no pose -> state NO_POSE", c.state() == PushupCounter.State.NO_POSE, "state=" + c.state());
        check("no pose -> count 0", c.count() == 0, "count=" + c.count());
    }

    private static void testReset() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        t = hold(c, 172, 8, t);
        t = ramp(c, 172, 62, 20, t);
        t = hold(c, 62, 8, t);
        t = ramp(c, 62, 172, 20, t);
        t = hold(c, 172, 8, t);
        c.reset();
        check("reset clears count", c.count() == 0, "count=" + c.count());
    }

    private static void testLostPoseResetsState() {
        PushupCounter c = new PushupCounter();
        long t = 1000;
        t = hold(c, 62, 10, t);
        boolean wasDown = c.state() == PushupCounter.State.DOWN;
        for (int i = 0; i < 100; i++) {  // 3.3 秒没人
            c.feed(Float.NaN, 0f, t);
            t += 33;
        }
        check("lost pose -> NO_POSE", c.state() == PushupCounter.State.NO_POSE, "wasDown=" + wasDown + " state=" + c.state());
        check("lost pose no count", c.count() == 0, "count=" + c.count());
    }

    private static void testAngleMath() {
        float straight = AngleMath.angleAt(0, 0, 0, 0, 1, 0, 0, 2, 0);      // 180
        float right = AngleMath.angleAt(0, 1, 0, 0, 0, 0, 1, 0, 0);         // 90
        float nan = AngleMath.angleAt(0, 0, 0, 0, 0, 0, 1, 1, 0);           // 重合点
        check("angle 180", Math.abs(straight - 180f) < 0.01f, "=" + straight);
        check("angle 90", Math.abs(right - 90f) < 0.01f, "=" + right);
        check("angle degenerate NaN", Float.isNaN(nan), "=" + nan);
    }

    private static void check(String name, boolean ok, String detail) {
        if (ok) { passed++; System.out.println("  ok   " + name); }
        else { failed++; System.out.println("  FAIL " + name + "  (" + detail + ")"); }
    }
}

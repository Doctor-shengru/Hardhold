package com.pushup.counter;

import android.Manifest;
import android.app.Activity;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.ImageFormat;
import android.hardware.camera2.CameraAccessException;
import android.hardware.camera2.CameraCaptureSession;
import android.hardware.camera2.CameraCharacteristics;
import android.hardware.camera2.CameraDevice;
import android.hardware.camera2.CameraManager;
import android.hardware.camera2.CaptureRequest;
import android.media.Image;
import android.media.ImageReader;
import android.os.Bundle;
import android.os.Handler;
import android.os.HandlerThread;
import android.os.Looper;
import android.os.SystemClock;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import com.google.mediapipe.framework.image.BitmapImageBuilder;
import com.google.mediapipe.tasks.components.containers.NormalizedLandmark;
import com.google.mediapipe.tasks.core.BaseOptions;
import com.google.mediapipe.tasks.vision.core.RunningMode;
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarker;
import com.google.mediapipe.tasks.vision.poselandmarker.PoseLandmarkerResult;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

public final class MainActivity extends Activity {

    private static final String TAG = "PushupCounter";
    private static final int REQ_CAMERA = 100;
    private static final int CAM_W = 480;
    private static final int CAM_H = 640;

    private static final int L_SHOULDER = 11, R_SHOULDER = 12;
    private static final int L_ELBOW = 13, R_ELBOW = 14;
    private static final int L_WRIST = 15, R_WRIST = 16;

    private PreviewView preview;
    private TextView hint;
    private Button resetButton;
    private Button tuneButton;
    private Button switchButton;
    private TunePanel tunePanel;

    private static final String PREFS = "pushup_tune";
    private static final String KEY_UP = "up_angle";
    private static final String KEY_DOWN = "down_angle";

    private final Handler ui = new Handler(Looper.getMainLooper());
    private final AtomicBoolean detecting = new AtomicBoolean(false);
    private final PushupCounter counter = new PushupCounter();

    private CameraManager cameraManager;
    private CameraDevice cameraDevice;
    private CameraCaptureSession session;
    private ImageReader imageReader;
    private HandlerThread camThread;
    private Handler camHandler;
    private int rotationDegrees = 270;
    /** true = 前置（默认，镜像显示）；false = 后置 */
    private boolean useFrontCamera = true;

    private PoseLandmarker landmarker;
    private volatile long detectStartedAt;
    private volatile long lastPoseAt;
    private long fpsStart;
    private int fpsFrames;
    private float fps;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setStatusBarColor(android.graphics.Color.TRANSPARENT);
        getWindow().setNavigationBarColor(android.graphics.Color.TRANSPARENT);
        buildUi();
        loadTunedAngles();
        initLandmarker();
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, REQ_CAMERA);
        }
    }

    private int dp(float v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    private void buildUi() {
        FrameLayout root = new FrameLayout(this);
        preview = new PreviewView(this);
        root.addView(preview, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));

        LinearLayout buttons = new LinearLayout(this);
        buttons.setOrientation(LinearLayout.HORIZONTAL);
        FrameLayout.LayoutParams bp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.RIGHT);
        bp.rightMargin = dp(12);
        bp.bottomMargin = dp(12);
        root.addView(buttons, bp);

        LinearLayout.LayoutParams bnp = new LinearLayout.LayoutParams(dp(72), dp(40));
        bnp.setMargins(dp(4), 0, dp(4), 0);

        switchButton = new Button(this);
        switchButton.setText("切换");
        switchButton.setAllCaps(false);
        switchButton.setTextColor(0xFFFFFFFF);
        switchButton.setTextSize(14);
        switchButton.setBackground(null);
        buttons.addView(switchButton, bnp);
        switchButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) { switchCamera(); }
        });

        tuneButton = new Button(this);
        tuneButton.setText("微调");
        tuneButton.setAllCaps(false);
        tuneButton.setTextColor(0xFFFFFFFF);
        tuneButton.setTextSize(14);
        tuneButton.setBackground(null);
        buttons.addView(tuneButton, bnp);
        tuneButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                tunePanel.setValues(counter.upAngle(), counter.downAngle());
                tunePanel.setLiveAngle(counter.angle());
                tunePanel.setVisibility(View.VISIBLE);
                tunePanel.post(new Runnable() {
                    @Override public void run() { updateGlassRects(); }
                });
            }
        });

        resetButton = new Button(this);
        resetButton.setText("重置");
        resetButton.setAllCaps(false);
        resetButton.setTextColor(0xFFFFFFFF);
        resetButton.setTextSize(14);
        resetButton.setBackground(null);
        buttons.addView(resetButton, bnp);
        resetButton.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View v) {
                counter.reset();
                preview.setStats(0, PushupCounter.State.NO_POSE, Float.NaN, fps);
                Toast.makeText(MainActivity.this, "已归零", Toast.LENGTH_SHORT).show();
            }
        });

        tunePanel = new TunePanel(this);
        tunePanel.setVisibility(View.GONE);
        FrameLayout.LayoutParams pp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM);
        pp.leftMargin = dp(12);
        pp.rightMargin = dp(12);
        pp.bottomMargin = dp(62);
        root.addView(tunePanel, pp);
        tunePanel.setListener(new TunePanel.Listener() {
            @Override public void onApply(float up, float down) {
                counter.setAngles(up, down);
                saveTunedAngles(up, down);
                Toast.makeText(MainActivity.this,
                        "已保存：撑起 " + Math.round(up) + "° / 下落 " + Math.round(down) + "°",
                        Toast.LENGTH_SHORT).show();
            }
            @Override public void onClose() {
                tunePanel.setVisibility(View.GONE);
                tunePanel.post(new Runnable() {
                    @Override public void run() { updateGlassRects(); }
                });
            }
        });

        hint = new TextView(this);
        hint.setTextColor(0xFFFFD666);
        hint.setTextSize(14);
        hint.setGravity(Gravity.CENTER);
        hint.setVisibility(View.GONE);
        FrameLayout.LayoutParams hp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM);
        hp.bottomMargin = dp(96);
        root.addView(hint, hp);

        setContentView(root);
        root.post(new Runnable() {
            @Override public void run() {
                int top = 0;
                if (android.os.Build.VERSION.SDK_INT >= 23) {
                    android.view.WindowInsets wi = root.getRootWindowInsets();
                    if (wi != null) top = wi.getSystemWindowInsetTop();
                }
                if (top <= 0) {
                    int id = getResources().getIdentifier("status_bar_height", "dimen", "android");
                    if (id > 0) top = getResources().getDimensionPixelSize(id);
                }
                preview.setTopInset(top + dp(8));
                updateGlassRects();
            }
        });

        getWindow().addFlags(android.view.WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        getWindow().setStatusBarColor(android.graphics.Color.TRANSPARENT);
        getWindow().getDecorView().setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                        | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN);
    }

    private void showHint(final String msg) {
        ui.post(new Runnable() {
            @Override public void run() {
                hint.setText(msg);
                hint.setVisibility(View.VISIBLE);
            }
        });
    }

    private void initLandmarker() {
        try {
            BaseOptions base = BaseOptions.builder()
                    .setModelAssetPath("pose_landmarker_lite.task")
                    .build();
            PoseLandmarker.PoseLandmarkerOptions options =
                    PoseLandmarker.PoseLandmarkerOptions.builder()
                            .setBaseOptions(base)
                            .setRunningMode(RunningMode.LIVE_STREAM)
                            .setNumPoses(1)
                            .setMinPoseDetectionConfidence(0.5f)
                            .setMinPosePresenceConfidence(0.5f)
                            .setMinTrackingConfidence(0.5f)
                            .setResultListener(new com.google.mediapipe.tasks.core.OutputHandler
                                    .ResultListener<PoseLandmarkerResult, com.google.mediapipe.framework.image.MPImage>() {
                                @Override public void run(PoseLandmarkerResult result,
                                                          com.google.mediapipe.framework.image.MPImage input) {
                                    onPoseResult(result);
                                }
                            })
                            .setErrorListener(new com.google.mediapipe.tasks.core.ErrorListener() {
                                @Override public void onError(RuntimeException e) {
                                    Log.e(TAG, "pose error", e);
                                }
                            })
                            .build();
            landmarker = PoseLandmarker.createFromOptions(this, options);
        } catch (Throwable t) {
            Log.e(TAG, "init landmarker failed", t);
            showHint("模型加载失败：" + t.getMessage());
        }
    }

    // ---------------- camera ----------------

    private void openCamera() {
        if (cameraDevice != null) return;
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) return;
        try {
            cameraManager = (CameraManager) getSystemService(CAMERA_SERVICE);
            String id = pickCamera(useFrontCamera);
            if (id == null) {
                // 请求的朝向不存在时退回另一个
                useFrontCamera = !useFrontCamera;
                id = pickCamera(useFrontCamera);
            }
            if (id == null) {
                showHint("没有找到可用的摄像头");
                return;
            }
            CameraCharacteristics ch = cameraManager.getCameraCharacteristics(id);
            Integer so = ch.get(CameraCharacteristics.SENSOR_ORIENTATION);
            if (so != null) rotationDegrees = so;

            if (camThread == null) {
                camThread = new HandlerThread("camera-thread");
                camThread.start();
                camHandler = new Handler(camThread.getLooper());
            }
            if (imageReader == null) {
                imageReader = ImageReader.newInstance(CAM_W, CAM_H, ImageFormat.YUV_420_888, 2);
                imageReader.setOnImageAvailableListener(new ImageReader.OnImageAvailableListener() {
                    @Override public void onImageAvailable(ImageReader reader) {
                        handleImage();
                    }
                }, camHandler);
            }
            cameraManager.openCamera(id, deviceCallback, camHandler);
        } catch (CameraAccessException | SecurityException e) {
            Log.e(TAG, "openCamera", e);
            showHint("打不开摄像头：" + e.getMessage());
        }
    }

    private String pickCamera(boolean front) throws CameraAccessException {
        int want = front ? CameraCharacteristics.LENS_FACING_FRONT
                : CameraCharacteristics.LENS_FACING_BACK;
        for (String id : cameraManager.getCameraIdList()) {
            CameraCharacteristics ch = cameraManager.getCameraCharacteristics(id);
            Integer facing = ch.get(CameraCharacteristics.LENS_FACING);
            if (facing != null && facing == want) return id;
        }
        return null;
    }

    /** 切换前后摄像头：关掉当前设备，稍等再开另一个 */
    private void switchCamera() {
        if (cameraDevice == null && session == null) return; // 摄像头没开，忽略
        useFrontCamera = !useFrontCamera;
        closeCamera();
        preview.setPose(null, false);
        ui.postDelayed(new Runnable() {
            @Override public void run() {
                openCamera();
                Toast.makeText(MainActivity.this,
                        useFrontCamera ? "已切换到前置摄像头" : "已切换到后置摄像头",
                        Toast.LENGTH_SHORT).show();
            }
        }, 350);
    }

    private final CameraDevice.StateCallback deviceCallback = new CameraDevice.StateCallback() {
        @Override public void onOpened(CameraDevice camera) {
            cameraDevice = camera;
            startSession();
        }

        @Override public void onDisconnected(CameraDevice camera) {
            camera.close();
            cameraDevice = null;
        }

        @Override public void onError(CameraDevice camera, int error) {
            camera.close();
            cameraDevice = null;
            showHint("摄像头错误 " + error);
        }
    };

    private void startSession() {
        if (cameraDevice == null || imageReader == null) return;
        try {
            cameraDevice.createCaptureSession(
                    java.util.Collections.singletonList(imageReader.getSurface()),
                    new CameraCaptureSession.StateCallback() {
                        @Override public void onConfigured(CameraCaptureSession s) {
                            session = s;
                            if (cameraDevice == null) return;
                            try {
                                CaptureRequest.Builder b =
                                        cameraDevice.createCaptureRequest(CameraDevice.TEMPLATE_PREVIEW);
                                b.addTarget(imageReader.getSurface());
                                b.set(CaptureRequest.CONTROL_MODE, CaptureRequest.CONTROL_MODE_AUTO);
                                session.setRepeatingRequest(b.build(), null, camHandler);
                            } catch (CameraAccessException e) {
                                Log.e(TAG, "preview request", e);
                            }
                        }

                        @Override public void onConfigureFailed(CameraCaptureSession s) {
                            showHint("相机预览配置失败");
                        }
                    }, camHandler);
        } catch (CameraAccessException e) {
            Log.e(TAG, "createCaptureSession", e);
        }
    }

    /** 按当前视图比例中心裁剪，让画面满屏，同时保证「看到的」就是「模型分析的」 */
    private Bitmap cropToViewAspect(Bitmap src) {
        int vw = preview.getWidth();
        int vh = preview.getHeight();
        if (vw <= 0 || vh <= 0) return src;
        float viewAspect = (float) vw / vh;
        float imgAspect = (float) src.getWidth() / src.getHeight();
        int w = src.getWidth(), h = src.getHeight();
        int cw = w, ch = h;
        if (imgAspect > viewAspect) {
            cw = Math.round(h * viewAspect);       // 太宽，裁两边
        } else if (imgAspect < viewAspect) {
            ch = Math.round(w / viewAspect);       // 太高，裁上下
        }
        if (cw == w && ch == h) return src;
        int x = (w - cw) / 2, y = (h - ch) / 2;
        Bitmap cropped = Bitmap.createBitmap(src, x, y, Math.max(1, cw), Math.max(1, ch));
        if (cropped != src) src.recycle();
        return cropped;
    }

    private void handleImage() {
        Image image = imageReader.acquireLatestImage();
        if (image == null) return;
        Bitmap bmp;
        try {
            bmp = YuvConverter.toUprightBitmap(image, rotationDegrees, useFrontCamera);
        } catch (Throwable t) {
            Log.e(TAG, "yuv convert", t);
            image.close();
            return;
        }
        image.close();
        final Bitmap frame = cropToViewAspect(bmp);
        ui.post(new Runnable() {
            @Override public void run() {
                preview.setFrame(frame);
            }
        });

        if (landmarker == null) return;
        // 检测器忙时跳过本帧；超过 800ms 没回来则视为卡住，强制解锁
        long now = SystemClock.uptimeMillis();
        if (detecting.get()) {
            if (now - detectStartedAt < 800) return;
            detecting.set(false);
        }
        if (!detecting.compareAndSet(false, true)) return;
        detectStartedAt = SystemClock.uptimeMillis();
        try {
            landmarker.detectAsync(new BitmapImageBuilder(frame).build(), detectStartedAt);
        } catch (Throwable t) {
            detecting.set(false);
            Log.e(TAG, "detectAsync", t);
        }
    }

    // ---------------- pose result ----------------

    private static float visOf(NormalizedLandmark l) {
        if (l.visibility().isPresent()) return l.visibility().get();
        if (l.presence().isPresent()) return l.presence().get();
        return 1f;
    }

    private static float sideAngle(List<NormalizedLandmark> lm, int s, int e, int w) {
        NormalizedLandmark a = lm.get(s), b = lm.get(e), c = lm.get(w);
        float v = Math.min(visOf(a), Math.min(visOf(b), visOf(c)));
        if (v < PushupCounter.MIN_VISIBILITY) return Float.NaN;
        return AngleMath.angleAt(a.x(), a.y(), a.z(), b.x(), b.y(), b.z(), c.x(), c.y(), c.z());
    }

    private void onPoseResult(PoseLandmarkerResult result) {
        try {
            long now = SystemClock.uptimeMillis();
            List<List<NormalizedLandmark>> poses = result.landmarks();
            if (poses == null || poses.isEmpty() || poses.get(0).size() < 33) {
                counter.feed(Float.NaN, 0f, now);
                ui.post(new Runnable() {
                    @Override public void run() {
                        preview.setPose(null, false);
                        updateStats();
                    }
                });
                return;
            }
            List<NormalizedLandmark> lm = poses.get(0);

            float left = sideAngle(lm, L_SHOULDER, L_ELBOW, L_WRIST);
            float right = sideAngle(lm, R_SHOULDER, R_ELBOW, R_WRIST);
            float angle;
            float vis;
            if (!Float.isNaN(left) && !Float.isNaN(right)) {
                angle = (left + right) / 2f;
                vis = 1f;
            } else if (!Float.isNaN(left)) {
                angle = left;
                vis = 1f;
            } else if (!Float.isNaN(right)) {
                angle = right;
                vis = 1f;
            } else {
                angle = Float.NaN;
                vis = 0f;
            }

            counter.feed(angle, vis, now);
            lastPoseAt = now;

            final float[] poseArr = new float[33 * 3];
            for (int i = 0; i < 33; i++) {
                NormalizedLandmark p = lm.get(i);
                poseArr[i * 3] = p.x();
                poseArr[i * 3 + 1] = p.y();
                poseArr[i * 3 + 2] = visOf(p);
            }

            fpsFrames++;
            if (now - fpsStart >= 1000) {
                fps = fpsFrames * 1000f / (now - fpsStart);
                fpsFrames = 0;
                fpsStart = now;
            }

            ui.post(new Runnable() {
                @Override public void run() {
                    preview.setPose(poseArr, true);
                    updateStats();
                }
            });
        } finally {
            detecting.set(false);
        }
    }

    /** 把需要玻璃底的控件矩形（屏幕坐标）交给 PreviewView 统一绘制 */
    private void updateGlassRects() {
        java.util.List<android.graphics.RectF> rects = new java.util.ArrayList<>();
        View[] views = (tunePanel.getVisibility() == View.VISIBLE)
                ? new View[]{switchButton, tuneButton, resetButton, tunePanel}
                : new View[]{switchButton, tuneButton, resetButton};
        int[] base = new int[2];
        preview.getLocationInWindow(base);
        int[] loc = new int[2];
        for (View v : views) {
            if (v.getWidth() == 0) continue;
            v.getLocationInWindow(loc);
            float x = loc[0] - base[0];
            float y = loc[1] - base[1];
            rects.add(new android.graphics.RectF(x, y, x + v.getWidth(), y + v.getHeight()));
        }
        preview.setGlassRects(rects);
    }

    private void updateStats() {
        preview.setStats(counter.count(), counter.state(), counter.angle(), fps);
        tunePanel.setLiveAngle(counter.angle());
    }

    private void loadTunedAngles() {
        SharedPreferences sp = getSharedPreferences(PREFS, MODE_PRIVATE);
        float up = sp.getFloat(KEY_UP, TunePanel.UP_DEFAULT);
        float down = sp.getFloat(KEY_DOWN, TunePanel.DOWN_DEFAULT);
        counter.setAngles(up, down);
        tunePanel.setValues(up, down);
    }

    private void saveTunedAngles(float up, float down) {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putFloat(KEY_UP, up)
                .putFloat(KEY_DOWN, down)
                .apply();
    }

    // ---------------- lifecycle ----------------

    @Override
    protected void onResume() {
        super.onResume();
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            openCamera();
        }
    }

    @Override
    protected void onPause() {
        closeCamera();
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (landmarker != null) {
            landmarker.close();
            landmarker = null;
        }
        if (camThread != null) {
            camThread.quitSafely();
            camThread = null;
            camHandler = null;
        }
        super.onDestroy();
    }

    private void closeCamera() {
        detecting.set(false);
        if (session != null) {
            session.close();
            session = null;
        }
        if (cameraDevice != null) {
            cameraDevice.close();
            cameraDevice = null;
        }
        if (imageReader != null) {
            imageReader.close();
            imageReader = null;
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode != REQ_CAMERA) return;
        if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            openCamera();
        } else {
            showHint("需要摄像头权限才能计数，请在系统设置里开启");
        }
    }
}

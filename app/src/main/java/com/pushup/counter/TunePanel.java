package com.pushup.counter;

import android.content.Context;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.SeekBar;
import android.widget.TextView;

/**
 * 屏幕下方的阈值微调面板：
 *   撑起阈值（角度 >= 此值算撑起）、下落阈值（角度 <= 此值算下落），
 * 支持「取当前」用实时肘角自动标定，避免手动猜数值。
 */
public final class TunePanel extends LinearLayout {

    public interface Listener {
        void onApply(float upAngle, float downAngle);
        void onClose();
    }

    /** 撑起阈值可调范围与默认值 */
    public static final int UP_MIN = 120, UP_MAX = 180, UP_DEFAULT = 158;
    /** 下落阈值可调范围与默认值 */
    public static final int DOWN_MIN = 40, DOWN_MAX = 120, DOWN_DEFAULT = 95;
    /** 两个阈值之间必须留出的最小间隔 */
    public static final int MIN_GAP = 15;

    private final TextView liveText;
    private final TextView upValue, downValue;
    private final TextView warnText;
    private final SeekBar upBar, downBar;

    private float liveAngle = Float.NaN;
    private Listener listener;

    public TunePanel(Context ctx) {
        super(ctx);
        setOrientation(VERTICAL);
        setPadding(dp(16), dp(12), dp(16), dp(10));

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xF0161D26);
        bg.setCornerRadius(dp(14));
        bg.setStroke(dp(1), 0x66FFFFFF);
        setBackground(bg);
        setElevation(dp(8));

        TextView title = new TextView(ctx);
        title.setText("微调计数阈值");
        title.setTextColor(Color.WHITE);
        title.setTextSize(16);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        addView(title);

        liveText = new TextView(ctx);
        liveText.setTextColor(0xFFFFD666);
        liveText.setTextSize(13);
        liveText.setText("当前肘角：--°");
        addView(liveText, marginTop(dp(4)));

        upBar = new SeekBar(ctx);
        upBar.setMax(UP_MAX - UP_MIN);
        upValue = new TextView(ctx);
        upValue.setTextColor(Color.WHITE);
        upValue.setTextSize(13);
        upValue.setGravity(Gravity.END);
        upValue.setMinWidth(dp(52));
        addSliderRow("撑起 ≥", upBar, upValue);

        downBar = new SeekBar(ctx);
        downBar.setMax(DOWN_MAX - DOWN_MIN);
        downValue = new TextView(ctx);
        downValue.setTextColor(Color.WHITE);
        downValue.setTextSize(13);
        downValue.setGravity(Gravity.END);
        downValue.setMinWidth(dp(52));
        addSliderRow("下落 ≤", downBar, downValue);

        warnText = new TextView(ctx);
        warnText.setTextColor(0xFFFF8A65);
        warnText.setTextSize(12);
        warnText.setVisibility(View.GONE);
        addView(warnText, marginTop(dp(2)));

        LinearLayout actions = new LinearLayout(ctx);
        actions.setOrientation(HORIZONTAL);
        actions.setGravity(Gravity.CENTER_VERTICAL);
        addView(actions, marginTop(dp(6)));

        Button upSnap = smallButton("取撑起");
        Button downSnap = smallButton("取下落");
        Button reset = smallButton("默认");
        Button done = smallButton("完成");

        actions.addView(upSnap, weight());
        actions.addView(downSnap, weight());
        actions.addView(reset, weight());
        actions.addView(done, weight());

        upBar.setOnSeekBarChangeListener(simpleListener());
        downBar.setOnSeekBarChangeListener(simpleListener());

        upSnap.setOnClickListener(new OnClickListener() {
            @Override public void onClick(View v) { snapUp(); }
        });
        downSnap.setOnClickListener(new OnClickListener() {
            @Override public void onClick(View v) { snapDown(); }
        });
        reset.setOnClickListener(new OnClickListener() {
            @Override public void onClick(View v) {
                setValues(UP_DEFAULT, DOWN_DEFAULT);
            }
        });
        done.setOnClickListener(new OnClickListener() {
            @Override public void onClick(View v) { apply(); }
        });

        setValues(UP_DEFAULT, DOWN_DEFAULT);
    }

    private void addSliderRow(String label, SeekBar bar, TextView value) {
        LinearLayout row = new LinearLayout(getContext());
        row.setOrientation(HORIZONTAL);
        row.setGravity(Gravity.CENTER_VERTICAL);
        addView(row, marginTop(dp(6)));

        TextView name = new TextView(getContext());
        name.setText(label);
        name.setTextColor(0xFFCFD8DC);
        name.setTextSize(13);
        row.addView(name, new LayoutParams(dp(44), LayoutParams.WRAP_CONTENT));

        row.addView(bar, new LayoutParams(0, dp(36), 1f));
        row.addView(value, new LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT));
    }

    private SeekBar.OnSeekBarChangeListener simpleListener() {
        return new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar bar, int progress, boolean fromUser) {
                updateValues();
            }
            @Override public void onStartTrackingTouch(SeekBar bar) {}
            @Override public void onStopTrackingTouch(SeekBar bar) {}
        };
    }

    private Button smallButton(String text) {
        Button b = new Button(getContext());
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setMinWidth(0);
        b.setMinimumWidth(0);
        b.setPadding(dp(4), 0, dp(4), 0);
        b.setBackgroundTintList(android.content.res.ColorStateList.valueOf(0xFF2C3A4A));
        b.setTextColor(Color.WHITE);
        return b;
    }

    private LayoutParams weight() {
        LayoutParams lp = new LayoutParams(0, dp(34), 1f);
        lp.setMargins(dp(3), 0, dp(3), 0);
        return lp;
    }

    private LinearLayout.LayoutParams marginTop(int px) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT);
        lp.topMargin = px;
        return lp;
    }

    private int dp(int v) {
        return Math.round(v * getResources().getDisplayMetrics().density);
    }

    public void setListener(Listener l) {
        this.listener = l;
    }

    /** 记录实时肘角，供「取当前」使用 */
    public void setLiveAngle(float angle) {
        this.liveAngle = angle;
        liveText.setText(Float.isNaN(angle) ? "当前肘角：--°"
                : "当前肘角：" + Math.round(angle) + "°（做动作时看这里）");
    }

    public void setValues(float up, float down) {
        upBar.setProgress(clamp(Math.round(up), UP_MIN, UP_MAX) - UP_MIN);
        downBar.setProgress(clamp(Math.round(down), DOWN_MIN, DOWN_MAX) - DOWN_MIN);
        updateValues();
    }

    private void updateValues() {
        int up = UP_MIN + upBar.getProgress();
        int down = DOWN_MIN + downBar.getProgress();
        upValue.setText(up + "°");
        downValue.setText(down + "°");
        boolean bad = up - down < MIN_GAP;
        warnText.setVisibility(bad ? View.VISIBLE : View.GONE);
        if (bad) warnText.setText("撑起阈值要比下落阈值大至少 " + MIN_GAP + "°");
    }

    private void snapUp() {
        if (Float.isNaN(liveAngle)) return;
        int up = clamp(Math.round(liveAngle), UP_MIN, UP_MAX);
        int down = DOWN_MIN + downBar.getProgress();
        if (up - down < MIN_GAP) up = clamp(down + MIN_GAP, UP_MIN, UP_MAX);
        upBar.setProgress(up - UP_MIN);
        updateValues();
    }

    private void snapDown() {
        if (Float.isNaN(liveAngle)) return;
        int down = clamp(Math.round(liveAngle), DOWN_MIN, DOWN_MAX);
        int up = UP_MIN + upBar.getProgress();
        if (up - down < MIN_GAP) down = clamp(up - MIN_GAP, DOWN_MIN, DOWN_MAX);
        downBar.setProgress(down - DOWN_MIN);
        updateValues();
    }

    private void apply() {
        int up = UP_MIN + upBar.getProgress();
        int down = DOWN_MIN + downBar.getProgress();
        if (up - down < MIN_GAP) {
            updateValues();
            return;
        }
        if (listener != null) listener.onApply(up, down);
        if (listener != null) listener.onClose();
    }

    private static int clamp(int v, int lo, int hi) {
        return v < lo ? lo : (v > hi ? hi : v);
    }
}

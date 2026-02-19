package com.moodaura;

import android.app.Activity;
import android.content.ContentResolver;
import android.provider.Settings;
import android.view.WindowManager;

import com.facebook.react.bridge.Promise;
import com.facebook.react.bridge.ReactApplicationContext;
import com.facebook.react.bridge.ReactContextBaseJavaModule;
import com.facebook.react.bridge.ReactMethod;

/**
 * Native module: screen brightness control.
 *
 * setBrightness / getBrightness operate on the current Activity's window.
 * dim(fraction) reduces current brightness by `fraction` (e.g. 0.20 → -20 %).
 * restore() resets to BRIGHTNESS_MODE_AUTOMATIC (-1 = follow system).
 *
 * Requires android.permission.WRITE_SETTINGS for Settings.System writes;
 * Window-level brightness needs no extra permission.
 */
public class BrightnessModule extends ReactContextBaseJavaModule {

    private float _savedBrightness = -1f;   // -1 = not saved

    public BrightnessModule(ReactApplicationContext ctx) { super(ctx); }

    @Override
    public String getName() { return "BrightnessModule"; }

    // ── get current window brightness (0–1) ──────────────────────────────────

    @ReactMethod
    public void getBrightness(Promise promise) {
        Activity a = getCurrentActivity();
        if (a == null) { promise.reject("NO_ACTIVITY", "No current activity"); return; }
        WindowManager.LayoutParams lp = a.getWindow().getAttributes();
        float b = lp.screenBrightness;
        // -1 means "follow system"; read system value instead
        if (b < 0) {
            try {
                ContentResolver cr = getReactApplicationContext().getContentResolver();
                b = Settings.System.getInt(cr, Settings.System.SCREEN_BRIGHTNESS) / 255f;
            } catch (Exception e) { b = 0.5f; }
        }
        promise.resolve((double) b);
    }

    // ── set absolute brightness (0–1) ────────────────────────────────────────

    @ReactMethod
    public void setBrightness(float brightness, Promise promise) {
        Activity a = getCurrentActivity();
        if (a == null) { promise.reject("NO_ACTIVITY", "No current activity"); return; }
        final float clamped = Math.max(0f, Math.min(1f, brightness));
        a.runOnUiThread(() -> {
            WindowManager.LayoutParams lp = a.getWindow().getAttributes();
            lp.screenBrightness = clamped;
            a.getWindow().setAttributes(lp);
            promise.resolve(null);
        });
    }

    // ── dim by a relative fraction (saves current value for restore) ─────────

    @ReactMethod
    public void dimBy(float fraction, Promise promise) {
        Activity a = getCurrentActivity();
        if (a == null) { promise.reject("NO_ACTIVITY", "No current activity"); return; }
        a.runOnUiThread(() -> {
            WindowManager.LayoutParams lp = a.getWindow().getAttributes();
            float current = lp.screenBrightness < 0 ? 0.8f : lp.screenBrightness;
            _savedBrightness = current;
            lp.screenBrightness = Math.max(0.05f, current * (1f - fraction));
            a.getWindow().setAttributes(lp);
            promise.resolve((double) lp.screenBrightness);
        });
    }

    // ── restore brightness saved by dimBy ────────────────────────────────────

    @ReactMethod
    public void restoreBrightness(Promise promise) {
        Activity a = getCurrentActivity();
        if (a == null) { promise.reject("NO_ACTIVITY", "No current activity"); return; }
        if (_savedBrightness < 0) { promise.resolve(null); return; }
        final float saved = _savedBrightness;
        _savedBrightness = -1f;
        a.runOnUiThread(() -> {
            WindowManager.LayoutParams lp = a.getWindow().getAttributes();
            lp.screenBrightness = saved;
            a.getWindow().setAttributes(lp);
            promise.resolve(null);
        });
    }
}

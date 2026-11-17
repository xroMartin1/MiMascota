package org.mimascota;

import android.content.Context;
import android.os.Bundle;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.messaging.FirebaseMessaging;
import java.util.EnumMap;
import java.util.UUID;
import org.json.JSONObject;
import java.util.Iterator;

/** SDK móvil; configuración pública y consentimiento, nunca credenciales de servidor. */
public final class FirebaseBridge {
    private static Context context;
    public static String deviceId(Context ctx) {
        android.content.SharedPreferences prefs = ctx.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE);
        String id = prefs.getString("device_id", "");
        if (id.isEmpty()) {
            id = UUID.randomUUID().toString();
            prefs.edit().putString("device_id", id).apply();
        }
        return id;
    }
    public static boolean canNotify(Context ctx) {
        return allowed(ctx, "notifications") && androidx.core.app.NotificationManagerCompat.from(ctx).areNotificationsEnabled() && (android.os.Build.VERSION.SDK_INT < 33
            || ctx.checkSelfPermission("android.permission.POST_NOTIFICATIONS") == android.content.pm.PackageManager.PERMISSION_GRANTED);
    }
    public static String token(Context ctx) {
        return canNotify(ctx) ? ctx.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).getString("push_token", "") : "";
    }
    public static boolean allowed(Context ctx, String key) {
        return ctx.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).getBoolean(key, false);
    }
    public static void initialize(Context ctx, String appId, String apiKey, String project, String sender) {
        context = ctx.getApplicationContext();
        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context, new FirebaseOptions.Builder()
                .setApplicationId(appId).setApiKey(apiKey).setProjectId(project).setGcmSenderId(sender).build());
        }
        analytics(allowed(context, "analytics"));
        FirebaseMessaging.getInstance().setAutoInitEnabled(allowed(context, "notifications"));
    }
    public static void analytics(boolean enabled) {
        context.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).edit().putBoolean("analytics", enabled).apply();
        FirebaseAnalytics sdk = FirebaseAnalytics.getInstance(context);
        EnumMap<FirebaseAnalytics.ConsentType, FirebaseAnalytics.ConsentStatus> consent = new EnumMap<>(FirebaseAnalytics.ConsentType.class);
        for (FirebaseAnalytics.ConsentType type : FirebaseAnalytics.ConsentType.values()) consent.put(type, FirebaseAnalytics.ConsentStatus.DENIED);
        consent.put(FirebaseAnalytics.ConsentType.ANALYTICS_STORAGE, enabled ? FirebaseAnalytics.ConsentStatus.GRANTED : FirebaseAnalytics.ConsentStatus.DENIED);
        sdk.setConsent(consent);
        sdk.setAnalyticsCollectionEnabled(enabled);
        if (!enabled) sdk.resetAnalyticsData();
    }
    public static void notifications(boolean enabled) {
        context.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).edit().putBoolean("notifications", enabled).apply();
        FirebaseMessaging sdk = FirebaseMessaging.getInstance();
        sdk.setAutoInitEnabled(enabled);
        if (enabled) sdk.getToken().addOnCompleteListener(task -> {
            if (task.isSuccessful() && allowed(context, "notifications")) {
                context.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).edit().putString("push_token", task.getResult()).apply();
            }
        });
        else {
            context.getSharedPreferences("mimascota_services", Context.MODE_PRIVATE).edit().remove("push_token").apply();
            sdk.deleteToken();
        }
    }
    public static void screen(String name) {
        if (context == null || !allowed(context, "analytics") || !isScreen(name)) return;
        Bundle data = new Bundle();
        data.putString(FirebaseAnalytics.Param.SCREEN_NAME, name);
        FirebaseAnalytics.getInstance(context).logEvent(FirebaseAnalytics.Event.SCREEN_VIEW, data);
    }
    private static boolean oneOf(String value, String... choices) {
        for (String choice : choices) if (choice.equals(value)) return true;
        return false;
    }
    private static boolean isScreen(String value) {
        return oneOf(value, "Inicio", "Mascotas", "Chapa", "Rutina", "Salud", "Cuenta", "Avisos", "Premium");
    }
    public static void event(String name, String parameters) {
        if (context == null || !allowed(context, "analytics") || parameters == null || parameters.length() > 1024) return;
        try {
            JSONObject values = new JSONObject(parameters);
            int expected;
            if (oneOf(name, "screen_view", "interaction")) expected = 1;
            else if ("screen_time".equals(name)) expected = 3;
            else if ("save_attempt".equals(name)) expected = 1;
            else if ("save_result".equals(name)) expected = 2;
            else if (oneOf(name, "care_complete", "payment_result", "usage_error")) expected = 1;
            else if ("pet_saved".equals(name)) expected = 0;
            else return;
            if (values.length() != expected) return;
            Bundle data = new Bundle();
            Iterator<String> keys = values.keys();
            while (keys.hasNext()) {
                String key = keys.next();
                Object raw = values.get(key);
                if ("screen_time".equals(name) && oneOf(key, "active_seconds", "idle_seconds")) {
                    if (!(raw instanceof Number)) return;
                    double value = ((Number) raw).doubleValue();
                    if (Double.isNaN(value) || Double.isInfinite(value) || value < 0 || value > 2147483647) return;
                    data.putDouble(key, value);
                    continue;
                }
                if (!(raw instanceof String)) return;
                String value = (String) raw;
                boolean valid = (oneOf(name, "screen_view", "interaction", "screen_time") && "screen".equals(key) && isScreen(value))
                    || (oneOf(name, "save_attempt", "save_result") && "operation".equals(key) && oneOf(value, "pet", "care", "health", "account"))
                    || ("save_result".equals(name) && "result".equals(key) && oneOf(value, "success", "validation", "failed", "abandoned"))
                    || ("care_complete".equals(name) && "result".equals(key) && oneOf(value, "completed", "undo"))
                    || ("payment_result".equals(name) && "result".equals(key) && oneOf(value, "approved", "rejected", "cancelled", "pending", "expired", "failed"))
                    || ("usage_error".equals(name) && "code".equals(key) && oneOf(value, "storage", "network", "validation", "auth", "payment"));
                if (!valid) return;
                data.putString(key, value);
            }
            if ("screen_view".equals(name)) {
                data.putString(FirebaseAnalytics.Param.SCREEN_NAME, data.getString("screen"));
                data.remove("screen");
            }
            FirebaseAnalytics.getInstance(context).logEvent(name, data);
        } catch (Exception ignored) {
            // Optional analytics must not interrupt the app.
        }
    }
}

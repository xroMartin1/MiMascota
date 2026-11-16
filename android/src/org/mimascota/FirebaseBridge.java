package org.mimascota;

import android.content.Context;
import android.os.Bundle;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.analytics.FirebaseAnalytics;
import com.google.firebase.messaging.FirebaseMessaging;
import java.util.EnumMap;
import java.util.UUID;

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
        if (!allowed(context, "analytics")) return;
        if (!(name.equals("Inicio") || name.equals("Mascotas") || name.equals("Rutina") || name.equals("Salud"))) return;
        Bundle data = new Bundle();
        data.putString(FirebaseAnalytics.Param.SCREEN_NAME, name);
        FirebaseAnalytics.getInstance(context).logEvent(FirebaseAnalytics.Event.SCREEN_VIEW, data);
    }
}

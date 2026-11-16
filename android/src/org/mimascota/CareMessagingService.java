package org.mimascota;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.os.Build;
import android.content.pm.PackageManager;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

/** Mensajes data-only: sin nombres, teléfonos ni detalles médicos en la pantalla bloqueada. */
public final class CareMessagingService extends FirebaseMessagingService {
    @Override public void onNewToken(String token) {
        if (FirebaseBridge.allowed(this, "notifications"))
            getSharedPreferences("mimascota_services", MODE_PRIVATE).edit().putString("push_token", token).apply();
    }
    @Override public void onMessageReceived(RemoteMessage message) {
        if ("qr_contact".equals(message.getData().get("kind"))) {
            QrContactNotifications.receive(this, message);
            return;
        }
        if (!FirebaseBridge.allowed(this, "notifications") || !"care".equals(message.getData().get("kind"))) return;
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        String channel = "care_reminders";
        if (Build.VERSION.SDK_INT >= 26)
            manager.createNotificationChannel(new NotificationChannel(channel, "Cuidados de tus mascotas", NotificationManager.IMPORTANCE_DEFAULT));
        Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
        if (launch == null) return;
        PendingIntent open = PendingIntent.getActivity(this, 0, launch, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, channel) : new Notification.Builder(this);
        boolean test = "true".equals(message.getData().get("test"));
        builder.setSmallIcon(Branding.notificationIcon(this))
            .setContentTitle(test ? "Notificaciones listas" : "Mi Mascota")
            .setContentText(test ? "Este es un aviso de prueba de Mi Mascota." : "Tienes un cuidado pendiente. Abre la app para revisarlo.")
            .setContentIntent(open).setAutoCancel(true);
        String event = message.getData().get("event_id");
        if (!test && event != null && event.matches("[a-f0-9-]{36}")) {
            android.content.SharedPreferences prefs = getSharedPreferences("mimascota_services", MODE_PRIVATE);
            synchronized (CareMessagingService.class) {
                try {
                    org.json.JSONArray recent = new org.json.JSONArray(prefs.getString("received_events", "[]"));
                    for (int i=0; i<recent.length(); i++) if (event.equals(recent.getString(i))) return;
                    recent.put(event);
                    org.json.JSONArray bounded = new org.json.JSONArray();
                    for (int i=Math.max(0,recent.length()-500); i<recent.length(); i++) bounded.put(recent.getString(i));
                    prefs.edit().putString("received_events", bounded.toString()).commit();
                } catch (org.json.JSONException ignored) { }
            }
        }
        manager.notify(event == null ? 101 : event.hashCode(), builder.build());
    }
}

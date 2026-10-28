package org.mimascota;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.messaging.RemoteMessage;

/** A push only announces a durable inbox entry, without names or contact data. */
public final class QrContactNotifications {
    private QrContactNotifications() {}
    public static void receive(Context context, RemoteMessage message) {
        if (!FirebaseBridge.allowed(context, "notifications")) return;
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission("android.permission.POST_NOTIFICATIONS") != PackageManager.PERMISSION_GRANTED) return;
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        String channel = "qr_contact_messages";
        if (Build.VERSION.SDK_INT >= 26) manager.createNotificationChannel(new NotificationChannel(channel, "Avisos de tus mascotas", NotificationManager.IMPORTANCE_DEFAULT));
        Intent launch = context.getPackageManager().getLaunchIntentForPackage(context.getPackageName());
        if (launch == null) return;
        PendingIntent open = PendingIntent.getActivity(context, 201, launch, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Builder builder = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(context, channel) : new Notification.Builder(context);
        builder.setSmallIcon(Branding.notificationIcon(context))
            .setContentTitle("Mi Mascota")
            .setContentText("Tienes un nuevo aviso. Abre la app para revisarlo.")
            .setContentIntent(open).setAutoCancel(true).setVisibility(Notification.VISIBILITY_PRIVATE);
        manager.notify(201, builder.build());
    }
}

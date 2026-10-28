package org.mimascota;

import android.content.Context;

/** A monochrome transparent icon for Android's notification tinting. */
public final class Branding {
    private Branding() {}
    public static int notificationIcon(Context context) {
        int icon = context.getResources().getIdentifier(
            "ic_mimascota_notification", "drawable", context.getPackageName());
        if (icon != 0) return icon;
        return context.getApplicationInfo().icon != 0
            ? context.getApplicationInfo().icon : android.R.drawable.ic_dialog_info;
    }
}

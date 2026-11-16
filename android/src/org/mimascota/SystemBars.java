package org.mimascota;

import android.app.Activity;
import android.graphics.Color;
import android.os.Build;
import android.view.View;
import android.view.Window;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;

/** Mantiene la superficie SDL y sus coordenadas táctiles dentro del área segura. */
public final class SystemBars {
    private SystemBars() {}

    public static void install(Activity activity) {
        activity.runOnUiThread(() -> {
            Window window = activity.getWindow();
            View content = activity.findViewById(android.R.id.content);
            if (content == null) return;
            content.setBackgroundColor(Color.WHITE);
            WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, window.getDecorView());
            controller.setAppearanceLightStatusBars(true);
            controller.setAppearanceLightNavigationBars(true);

            // Antes de Android 15, fullscreen=0 ya deja las barras fuera de SDL.
            if (Build.VERSION.SDK_INT < 35) {
                window.setStatusBarColor(Color.WHITE);
                if (Build.VERSION.SDK_INT >= 26) window.setNavigationBarColor(Color.WHITE);
                return;
            }
            WindowCompat.setDecorFitsSystemWindows(window, false);
            content.setFitsSystemWindows(false);
            ViewCompat.setOnApplyWindowInsetsListener(content, (view, insets) -> {
                Insets safe = insets.getInsets(WindowInsetsCompat.Type.systemBars()
                        | WindowInsetsCompat.Type.displayCutout());
                // Valores absolutos: volver desde segundo plano no acumula espacios.
                view.setPadding(safe.left, safe.top, safe.right, safe.bottom);
                // El teclado mantiene su dispatch; Kivy conserva below_target.
                return insets;
            });
            ViewCompat.requestApplyInsets(content);
        });
    }
}

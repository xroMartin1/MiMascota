package org.mimascota;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/** Session encrypted with an app-private, non-exportable Android Keystore key. */
public final class SessionVault {
    private static final String ALIAS = "mimascota_session_v1";
    private SessionVault() {}
    private static SecretKey key() throws Exception {
        KeyStore store = KeyStore.getInstance("AndroidKeyStore");
        store.load(null);
        if (!store.containsAlias(ALIAS)) {
            KeyGenerator generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).setKeySize(256).build());
            generator.generateKey();
        }
        return (SecretKey) store.getKey(ALIAS, null);
    }
    public static synchronized boolean save(Context context, String token) { return saveAt(context, token, ALIAS); }
    public static synchronized boolean saveFlow(Context context, String token) { return saveAt(context, token, ALIAS + "_flow"); }
    private static boolean saveAt(Context context, String token, String name) {
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.ENCRYPT_MODE, key());
            byte[] encrypted = cipher.doFinal(token.getBytes(java.nio.charset.StandardCharsets.UTF_8));
            return context.getSharedPreferences(name, Context.MODE_PRIVATE).edit()
                .putString("iv", Base64.encodeToString(cipher.getIV(), Base64.NO_WRAP))
                .putString("value", Base64.encodeToString(encrypted, Base64.NO_WRAP)).commit();
        } catch (Exception ignored) { return false; }
    }
    public static synchronized String read(Context context) { return readAt(context, ALIAS); }
    public static synchronized String readFlow(Context context) { return readAt(context, ALIAS + "_flow"); }
    private static String readAt(Context context, String name) {
        android.content.SharedPreferences prefs = context.getSharedPreferences(name, Context.MODE_PRIVATE);
        String value = prefs.getString("value", "");
        if (value.isEmpty()) return "";
        try {
            Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE, key(), new GCMParameterSpec(128, Base64.decode(prefs.getString("iv", ""), Base64.NO_WRAP)));
            return new String(cipher.doFinal(Base64.decode(value, Base64.NO_WRAP)), java.nio.charset.StandardCharsets.UTF_8);
        } catch (Exception ignored) { return ""; }
    }
    public static synchronized void clearFlow(Context context) {
        context.getSharedPreferences(ALIAS + "_flow", Context.MODE_PRIVATE).edit().clear().commit();
    }
    public static synchronized void clear(Context context) {
        context.getSharedPreferences(ALIAS, Context.MODE_PRIVATE).edit().clear().commit();
    }
}

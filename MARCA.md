# Marca de Mi Mascota

Logo aprobado el 10 de octubre de 2026: huella con QR simbólico, blanco sobre azul petróleo #103D49. Se conserva el QR real de cada mascota por separado; el símbolo del logo no se escanea.

## Recursos de la app

- `assets/brand/logo-negativo.png`: cabecera común.
- `assets/brand/logo-azul.png` y `logo-positivo.png`: variantes auxiliares transparentes.
- `assets/brand/icono-app.png`: icono tradicional de Android y ventana de escritorio.
- `assets/brand/icono-adaptive.png` e `icono-background.png`: capas adaptables de Android con margen para máscaras del sistema.
- `assets/brand/arranque.png`: imagen previa a la carga de Kivy.
- `android/res/drawable/ic_mimascota_notification.png`: silueta blanca transparente para avisos del sistema; no usar el icono de app con fondo en ese lugar.

La geometría vectorial y el kit SVG/PNG están en MiMascotaWeb, `design/logo-definitivo`. Se regeneran con `node tools/build-brand-assets.mjs` desde ese repositorio.

## Android

La APK de revisión es `apk/mimascota-0.2.3-logo.apk`, generada con `tools/build_brand_android.sh` en `/home/marco/MiMascotaBrand`, separado de los builds anteriores. El snapshot usa `tools/build_qr_snapshot.py 0.2.3 brand-0.2.3-source.zip` y excluye cuentas, datos de usuario y cachés.

Instalar como actualización de la app existente para ver el icono nuevo. No desinstalar ni borrar datos para cambiar la marca. La descarga pública permanece en la beta previamente autorizada hasta probar esta actualización en un teléfono.

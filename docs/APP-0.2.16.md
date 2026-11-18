# Correcciones de Android 0.2.16

## Compartir PDF y estadísticas

Ambos botones utilizan `services.health_report.share_health_report`. La APK 0.2.15 ya contenía FileProvider, autoridad privada y rutas estrechas para `health-reports/` y `usage-exports/`. El fallo compartido estaba en la resolución de sobrecargas Java al pasar un Uri sin tipo explícito a Intent.putExtra. Se reprodujo con pyjnius y JVM reales; el cast a `android.os.Parcelable` selecciona la sobrecarga correcta.

Se conserva MIME, ClipData y permiso temporal de lectura; no se abren directorios adicionales ni se piden permisos generales de almacenamiento. Los mensajes ahora distinguen preparación del archivo y apertura del menú para compartir. La comprobación definitiva de aplicaciones receptoras requiere instalar una APK recompilada en Android.

## Premium

Registrar mascotas es independiente de Premium. La prueba gratuita de chapa es única por cuenta y no se reinicia al eliminar a la mascota. Borrar la mascota no transfiere su plan a otra. Abrir Premium sin chapa muestra la acción necesaria y lleva a la pantalla Chapa respetando el estado de la prueba.

Los beneficios de ficha activa y mismo QR se identifican como Premium; la chapa física se identifica como primera compra. No se convierten en funciones de pago el historial, cuidados ni exportaciones.

## Navegación

Los cinco botones se conservan entre pantallas. Un único indicador lima recorre la barra en 220 ms, continúa desde su posición si se pulsa otra pestaña y se ajusta al cambiar tamaño. La preferencia de movimiento reducido evita el recorrido. Se conserva la respuesta al pulsar y el fundido suave de contenido.

## Métricas y JSON

`services/measurement.py` guarda métricas en el almacenamiento privado de la app, subcarpeta `usage/<identificador>.json`. Los campos incluyen eventos, participantes seudónimos, cobertura, segmentos y finalizaciones. `screens/measurement.py` exporta una copia y comparte mediante el mismo puente corregido del PDF.

El dashboard web automático es independiente: consulta agregados de Firebase/GA4 con una credencial de lectura en servidor y permite entrar por código. El código y las credenciales no van en el APK. El JSON sigue permitiendo demostrar y recalcular los KPIs MJV detallados; Firebase no recibe todos esos datos ni reemplaza los denominadores locales.

No se ha compilado ni instalado esta versión en esta entrega. Compilar 0.2.16 en el equipo WSL habitual, instalarla encima de la anterior con el mismo certificado y comprobar ambos menús de compartir, navegación, permisos y flujos Premium. No presentar tests de escritorio como una verificación de hardware Android.

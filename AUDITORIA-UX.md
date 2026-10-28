# Revisión de UI/UX · Mi Mascota 0.2.1

Revisión técnica y visual de la aplicación con datos ficticios. No equivale a una investigación con participantes ni a una validación física en todos los teléfonos.

| Problema observado | Corrección |
| --- | --- |
| Hueco bajo títulos sin subtítulo, especialmente Mi cuenta | No se añade un subtítulo vacío; títulos y subtítulos ajustan su altura al texto. |
| QR presentado como disponible sin cuenta, aunque el flujo la exige | Inicio explica la cuenta y Chapa muestra una acción explícita para registrarse/iniciar sesión. |
| Dos pestañas parecían seleccionadas por el fondo permanente de Chapa | El QR solo muestra su fondo activo cuando se abre esa sección. |
| Accesos repetidos a Rutina en Inicio | Se elimina el enlace duplicado; se conserva el siguiente cuidado y la navegación inferior. |
| Banner de cuidados demasiado alto y con textos superpuestos | Banner compacto, un solo título y banda de contraste; el botón de añadir aparece antes. |
| Nombre largo o texto de salud cortado | Nombre y resumen crecen según el texto; títulos de detalle y etiquetas de formularios admiten varias líneas. |
| Zonas mostradas como identificadores técnicos | Se muestran ciudades y países; el identificador IANA se conserva internamente. |
| Configuración larga y acción «Publicar calendario» | Descripción más directa y acción «Guardar recordatorios», conservando la advertencia de reemplazo entre teléfonos. |
| Fechas de tarjetas en formato de almacenamiento | Presentación «Hoy · 18:30», «Mañana · 09:00» o «12 oct · 09:00»; no se cambia la fecha almacenada. |
| Cifras de pendientes que incluían los atrasados de otra columna | En Inicio, ambas cifras representan grupos distintos. |
| Transiciones lentas y filas sin respuesta al pulsar | Transición de 180 ms con menor cambio de opacidad; las filas cambian de fondo al pulsarlas. Se conserva el respeto por animaciones desactivadas en Android. |

Se simplificaron textos («Sus cuidados», «Su salud», «Añadir al historial») y se aclaró que los datos del invitado ya se guardan en el teléfono. La cuenta añade recuperación en otros dispositivos. El tamaño de los inputs usa `sp` para respetar la escala de texto.

## Verificación

- 56 pruebas de lógica existentes aprobadas.
- Flujos de invitado, registro de mascota, completar cuidado, historial y persistencia con Kivy real.
- Cuenta, avisos, conversación, QR y configuración de recordatorios con backend simulado.
- Capturas de Inicio, Mascotas, Rutina, Salud, Cuenta y Chapa a 390 y 320 píxeles; nombres y tareas largos. Se comprueban límites horizontales, altura de textos multilínea y ausencia de solapamiento en encabezados.
- Prueba reutilizable: `tools/check_layout_review.py`. Las capturas van a `previews/layout-review` o a `AUDIT_OUTPUT` si se define.

El control antiguo esperaba un diálogo de cuenta que ahora es una página; se actualizó para comprobar la navegación real. El test de recordatorios aísla la restauración de sesión ficticia. No se debilitaron verificaciones de guardado o permisos.

Para comprobar en el teléfono: instalar el APK sobre la versión anterior, recorrer las pestañas, abrir formularios con el teclado, probar nombres largos y revisar cuenta/avisos con sesión. Las pruebas de escritorio no sustituyen esas comprobaciones de Android.

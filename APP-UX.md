# UX de Mi Mascota · beta 0.2.0

## Criterios

- Una acción principal por vista. Texto breve, vocabulario cotidiano y objetivos táctiles de al menos 44 dp.
- Cuenta, Avisos y Chapa son páginas; los diálogos se reservan para formularios, confirmaciones y opciones poco frecuentes.
- Espera de red con spinner discreto, sin mensajes tranquilizadores repetidos.
- La campana entra directamente en Avisos. Una fila agrupa mascota, mensaje, fecha y estado sin leer; los cuidados pendientes aparecen en la misma pantalla.
- La conversación se lee y responde en la misma vista. Archivo, bloqueo y cierre quedan en opciones.
- Cuenta: nombre antes que correo, lápiz para editar, y tres entradas principales. Exportación y recuperación quedan en Ajustes → Datos y respaldos; el guardado local continúa siendo parte del funcionamiento de la app.
- Invitado: “Regístrate o inicia sesión para guardar tus datos”. No se exige cuenta para cuidados locales.
- QR cuadrado, nítido y casi del ancho disponible. La prueba se explica antes de confirmar, y no se inicia al abrir la página.

## Sesión

La sesión se guarda en el almacén privado de Android cifrada con AES-GCM y una clave no exportable de Android Keystore. No se escribe en las copias JSON de mascotas ni se guarda contraseña. Se conserva URL del proyecto, tokens, vencimiento y datos mínimos del perfil. El servidor sigue verificando la identidad en todas las acciones autenticadas; los metadatos locales no conceden acceso.

Una sesión aún vigente se carga sin esperar red. Una sesión vencida se renueva y guarda los tokens rotados; si no hay conexión conserva el acceso a los datos locales de esa cuenta y reintenta al necesitar red. El cierre de sesión elimina la copia cifrada, incluso si falla la conexión. Una actualización con el mismo paquete y firma mantiene el almacén. La primera instalación de 0.2.0 necesita iniciar sesión porque 0.1.x solo conservaba los tokens en memoria.

Referencias: [Android Keystore/AES-GCM](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec), [sesiones y renovación de Supabase](https://supabase.com/docs/guides/auth/sessions).

## Una prueba por cuenta

La chapa pertenece a una mascota. Cada cuenta dispone de una sola prueba de 14 días. `qr_private.trial_entitlements` conserva el uso y sus fechas aunque se elimine la mascota o el registro de la chapa. No tiene FK a mascota/chapa; solo a la cuenta. Las fechas proceden del servidor.

Las chapas anteriores mantienen su vencimiento original; no se revocaron en bloque. Las nuevas emisiones quedan limitadas por el registro de prueba de la cuenta. No se implementan compra, suscripciones ni emisión de chapas físicas.

## Verificación

APK de prueba: `apk/mimascota-0.2.0-ux.apk`, mismo paquete y certificado que 0.1.x. Instalar como actualización, sin borrar datos. El número de versión del proyecto también queda en 0.2.0 para evitar futuras compilaciones con una versión anterior.

- Pruebas de sesión: carga sin red, renovación/rotación, fallo de red, invalidación, cierre y proyecto diferente.
- SQL transaccional: segunda mascota bloqueada, mismo QR sin renovación, eliminación de mascota/chapa y revocación sin nuevas pruebas, ledger privado.
- Kivy real: jerarquía de cuenta, lápiz, entrada directa a Avisos, fila con vista previa/fecha, respuesta en línea, lectura tras renderizar y QR mayor de 290 dp en 390 px; revisión de 320 px.
- Compilación aislada Android, firma compatible, módulos/KV y clase Keystore comprobados en la APK. La persistencia tras cerrar/actualizar y la ergonomía con teclado requieren confirmación en un teléfono real.

## Siguientes mejoras

- Resolver conflictos de sincronización con comparación de cambios, conservando ambas versiones. La app no sobrescribe silenciosamente una copia distinta.
- Evaluar sincronización automática con ese control de conflictos. Actualmente “Guardar cambios” publica la copia completa de la cuenta.
- Probar tamaños de texto de accesibilidad, teclado y lectores de pantalla en Android físico. Los iconos tienen objetivos grandes; falta validar su anuncio por TalkBack.

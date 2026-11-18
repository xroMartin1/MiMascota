# Analítica y evaluación: Medir, Jugar, Validar

Esta guía aplica el método de la diapositiva del curso y la rúbrica E4. La instrumentación es código; los resultados requieren participantes y un periodo de recogida real. Los fixtures y capturas de comprobación no son evidencia de impacto social.

## Medir

Antes de probar, registrar en la ficha del estudio:

| Campo | Qué completar antes de recoger datos |
| --- | --- |
| Pregunta | Qué obstáculo o beneficio de Mi Mascota se quiere evaluar. |
| Cohorte | Participantes invitados o pruebas del equipo; no mezclarlas. |
| Periodo | Inicio inclusivo y fin exclusivo con fecha, hora y zona. |
| Muestra | Número previsto, criterios de selección y dispositivos. Al finalizar, número realmente observado. |
| Metas | Umbral por KPI elegido antes de ver los resultados y motivo de ese umbral. |
| Tareas | Registrar mascota, crear un cuidado, reiniciar y verificar persistencia, completar cuidado, consultar Salud y recorrer Webpay sandbox. |
| Custodia | Responsable de exportaciones, acceso restringido y fecha de eliminación. |

No hay una muestra, metas ni resultados reales precargados. Una muestra de conveniencia pequeña no representa a todos los dueños de mascotas. No calcular retención de siete días sin observar ese periodo.

### Activar y registrar una prueba

1. Abrir **Cuenta → Privacidad y estadísticas**. Aceptar es opcional; no afecta mascotas, cuidados o la cuenta. Confirmar la zona horaria de los cuidados, también si los recordatorios están desactivados.
2. Volver a ese apartado y elegir **Participar en una prueba de uso**. Elegir Participante o Equipo. Un campo vacío genera un código aleatorio de 32 caracteres; no escribir nombres o correos. Reutilizar el mismo código si la misma persona participa en otro dispositivo. Mantener una ficha externa mínima de invitaciones consentidas y evitar duplicar personas.
3. Para activación, usar una cuenta o invitado sin mascotas al comenzar. Quien ya tiene mascotas se considera participante existente y no entra en el denominador de primera activación. No borrar datos reales para preparar una prueba.
4. Realizar las tareas y anotar por separado dificultades, ayuda recibida y observaciones. El tiempo de inactividad no explica por sí solo el motivo de una pausa.
5. Elegir **Compartir mis estadísticas** y confirmar destinatario. El archivo JSON incluye códigos y referencias seudónimas locales, no nombres, contactos ni historial sanitario. Contiene datos de evaluación; no subirlo al repositorio.

Al desactivar estadísticas se detiene la medición y se borran registros de evaluación locales de las cuentas del dispositivo, incluidos temporales. Los datos funcionales de cuidados y pagos se conservan. Si falla la persistencia o el borrado, se informa y debe reintentarse; la medición local se detiene en la sesión actual. La revocación no promete borrar automáticamente las copias ya compartidas ni los datos que ya recibió Google.

La retención local es de 30 días y se aplica al ejecutar el motor. No hay proceso que purgue con la app cerrada. La configuración de retención y solicitudes de eliminación en Google y la custodia de exportaciones se gestionan por separado.

### Diccionario de eventos

| Evento | Parámetros permitidos | Disparador |
| --- | --- | --- |
| `screen_view` | `screen` fijo | Cambio de pantalla lógica; un refresco no cuenta otra visita. |
| `interaction` | `screen` fijo | Toque o tecla en primer plano; no registra coordenadas ni caracteres. No equivale exclusivamente a un clic en botón. |
| `screen_time` | `screen`, `active_seconds`, `idle_seconds` | Vacía un intervalo al interactuar, navegar, suspender o exportar. Inactividad desde 30 segundos sin interacción. |
| `save_attempt` | `operation`: pet/care/health/account | Intento de guardar un formulario instrumentado. |
| `save_result` | `operation`, `result`: success/validation/failed/abandoned | Resultado de validación, persistencia o solicitud. Cuenta cubre el guardado de perfil; no implica todos los flujos de autenticación. |
| `pet_saved` | Ninguno | Creación confirmada de mascota; editar o fallar el guardado no lo dispara. |
| `care_complete` | `result`: completed/undo | Finalización o reapertura después de guardar. Las fechas y referencias permanecen solo en el registro local. |
| `usage_error` | `code`: storage/network/validation/auth/payment | Clasificación fija de error. Instrumentados almacenamiento, red y validación; auth/payment se reservan para futuras clasificaciones específicas. Nunca envía mensajes de error. |
| `payment_result` | Resultado fijo | Esquema disponible, pero no se emite al refrescar Premium para evitar duplicados. El KPI de pagos usa órdenes del servidor. |

Pantallas: Inicio, Mascotas, Chapa, Rutina, Salud, Cuenta, Avisos y Premium. Conversación se agrupa en Avisos y cuidados compartidos en Cuenta. No se envían a Firebase códigos de participante, grupo, ID de cuenta, mascota o cuidado, fechas de cuidados, QR, raza, texto médico, datos de tarjeta ni secretos.

En Android se desactiva el registro automático de pantalla de Activity: Kivy tiene una actividad para varias pantallas y la app registra la navegación lógica. Los SDK pueden recopilar sus eventos automáticos y metadatos técnicos propios después del consentimiento; el diccionario anterior limita nuestros eventos personalizados.

### KPIs y fuentes

| KPI | Numerador / denominador | Exclusiones y lectura |
| --- | --- | --- |
| Activación | Participantes nuevos que guardan primera mascota / participantes nuevos inscritos en el periodo. | Códigos únicos, cohorte evaluation. No tratar instalaciones o cuentas como personas. |
| Cumplimiento | Ocurrencias completadas al corte / ocurrencias previstas en `[inicio,fin)` durante la cobertura observada. | Cancelaciones antes de vencer excluidas; vencidas conservadas aunque luego se borre rutina. Sin fecha se muestra aparte. Separar completadas tarde. |
| Éxito de guardado | success / (success + failed), por operación. | Validación, abandono y número de intentos separados. No medir disponibilidad global con esta tasa. |
| Pago sandbox | Órdenes active / órdenes terminales (active, rejected, cancelled, expired). | Identificador único, datos del servidor, pendientes aparte. Es una prueba de recorrido, no ingresos o ventas reales. Un rechazo previsto por el guion también es un caso funcional correcto. |

Un denominador cero produce **Sin datos**, nunca un porcentaje inventado. Cambiar participante vacía los tiempos anteriores y cierra sus intervalos. La zona IANA conserva los cambios de horario. Cada repetición se identifica por referencia de tarea y vencimiento. El mismo participante y tarea en dos teléfonos comparten referencia seudónima; se deduplican al consolidar. Los eventos anteriores al consentimiento o a la cobertura no se reconstruyen.

Los datos de Firebase y del registro local tienen cobertura y formas de entrega diferentes. El registro local calcula los KPIs exactos; Firebase sirve para explorar navegación y comprobar recepción. Los códigos de cohorte no se envían a Google: para separar tráfico técnico allí se deben configurar filtros de desarrollo o una propiedad de pruebas; no suponer que el filtro local cambia los informes de Google.

## Jugar

El participante usa tareas acordadas, sin que el equipo las ejecute en su lugar. Registrar ayudas y fallos. Probar sin conexión y volver a abrir para comprobar persistencia. En pagos, usar solo tarjetas de integración oficiales y anotar si el caso esperado era aprobar, rechazar o anular. No usar datos reales de terceros en la demostración.

La persona puede rechazar las estadísticas y aun así dar feedback cualitativo voluntario; no incluirla en el denominador instrumentado sin indicarlo. Mantener todas las pruebas del equipo fuera de la cohorte evaluation.

## Validar y generar el informe

Desde la carpeta del proyecto, con Python y las dependencias instaladas:

```bash
python tools/report_measurement.py /ruta/uso-1.json /ruta/uso-2.json --start 2026-11-17T09:00:00-03:00 --end 2026-11-18T09:00:00-03:00 --cohort evaluation --output data/evaluacion
```

Las fechas son un **ejemplo de comando**, no un periodo ya observado. Reemplazarlas por el periodo acordado. Para Equipo, usar `--cohort team`. Para pagos, añadir `--payments /ruta/webpay-orders.json --payment-orders /ruta/ordenes-participantes.json`. El primer archivo es la exportación mínima autenticada descrita en `WEBPAY-SANDBOX.md` del repositorio web. El segundo es una selección de referencias anotadas por el operador durante la prueba desde el registro administrativo: `{"cohort":"evaluation","order_ids":["UUID-DE-LA-ORDEN-OBSERVADA"]}`. La UI habitual ya no muestra la referencia de pago; realizar y documentar los casos de forma que el operador pueda identificar cada orden del snapshot. Usar referencias reales de orden, nunca tokens. Para Equipo, la selección debe indicar `team`. El snapshot del servidor puede incluir ambas cohortes: el informe exige la selección para no mezclar pruebas del equipo con participantes. No entregar secretos ni usar una lista inventada como si viniera del servidor.

El comando produce:

- `summary.json`: cifras y cobertura por conjunto; snapshots repetidos del mismo conjunto usan el más reciente.
- `events.csv`: filas mínimas para revisar cálculos, con códigos seudónimos. Se debe custodiar como dato de evaluación.
- `report.html`: gráficos legibles, imprimibles como PDF desde el navegador. Sin scripts externos, servicios de pago ni resultados de demostración precargados.

La cobertura se corta en la fecha de extracción de cada dispositivo; un export viejo no genera cuidados futuros imaginarios. No sumar informes agregados de varios teléfonos a mano: consolidar sus exportaciones juntas para deduplicar participantes y ocurrencias. Las órdenes muestran su estado al exportar: no reconstruyen el estado histórico que tenían al final del periodo de creación.

Para cada hallazgo, escribir: dato y fuente, interpretación con contexto, incertidumbre, mejora concreta, impacto/esfuerzo y comprobación posterior. Ejemplo de plantilla: «X de N personas completaron [tarea] en [periodo]. Observamos [obstáculo]. Proponemos [cambio]. Lo contrastaremos con [prueba]». Completar con datos reales, sin atribuir a Firebase observaciones manuales.

## Comprobar Firebase Android

Firebase Analytics no requiere contratar otro producto ni BigQuery para estos eventos e informes. El proyecto debe tener Analytics habilitado y configuración pública Android válida; ver `ANDROID-SERVICIOS.md`.

```bash
adb shell setprop debug.firebase.analytics.app org.mimascota.mimascota
```

Activar estadísticas en la app, navegar y guardar una mascota de prueba. En Firebase abrir Analytics → DebugView y comprobar nombre y parámetros. Rechazar/revocar y comprobar que no se envían nuevos eventos propios. Finalizada la comprobación:

```bash
adb shell setprop debug.firebase.analytics.app .none.
```

DebugView verifica instrumentación, no impacto ni muestra de usuarios. La entrega normal puede ser diferida. Configurar filtros de tráfico de desarrollo según la propiedad; no asumir que DebugView por sí solo separa todos los datos de pruebas.

Fuentes: [Analytics y precios](https://firebase.google.com/pricing), [pantallas manuales](https://firebase.google.com/docs/analytics/screenviews), [DebugView](https://firebase.google.com/docs/analytics/debugview), [nombres reservados](https://support.google.com/analytics/answer/13316687).

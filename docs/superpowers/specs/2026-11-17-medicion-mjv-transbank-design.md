# Medición MJV y Webpay Plus de prueba

Estado: diseño aprobado por el usuario el 17 de noviembre de 2026; implementación en ramas aparte, sin despliegue.

## Decisiones y finalidad

El usuario eligió Firebase si permite medir gratuitamente, Transbank en sandbox y renovación manual. La diapositiva de clase define MJV como «Medir, Jugar, Validar» y menciona clics y tiempos muertos en pantalla. La rúbrica exige indicadores operacionalizados, periodo declarado, fuentes verificables, gráficos e interpretación. No basta con instalar el SDK.

Objetivo: demostrar uso real de Mi Mascota y detectar mejoras con evidencia, además de sustituir el checkout de Mercado Pago por un pago con tarjeta de prueba que habilite un mes de Premium por mascota a $3.990 CLP.

## Alternativas

- Firebase Analytics y registro local mínimo de evaluación: aprovecha el SDK Android existente, mantiene informes gratuitos y permite explicar y exportar los cálculos aunque no haya conexión. Recomendación técnica; no requiere BigQuery, otro proveedor ni Firebase Auth.
- Solo Firebase: menos trabajo local, pero no garantiza un cálculo exacto del cumplimiento de cuidados a partir de contadores de eventos, especialmente con recurrencias, deshacer y reintentos. Se descarta como única fuente de ese KPI.
- Solo registro local: funciona en escritorio y sin conexión, pero obliga a consolidar manualmente los dispositivos y no aprovecha la preferencia del usuario por Firebase.

Para pagos se eligió Webpay Plus con renovación manual. Oneclick y el cobro automático quedan fuera del alcance elegido. Los servicios reales de pago tienen condiciones comerciales distintas del entorno de integración; esta entrega sigue siendo una demostración sin dinero real.

## MJV y evidencia

1. Medir: declarar preguntas, indicadores, fórmulas, instrumentación, cohorte, zona horaria y periodo antes de recoger resultados. Separar datos técnicos del equipo de participantes de prueba.
2. Jugar: participantes que hayan aceptado realizan tareas: registrar mascota, programar cuidado, cerrar y abrir la app, completar cuidado, consultar salud y probar el recorrido de pago. Registrar obstáculos y observaciones; los clics por sí solos no explican por qué ocurre un problema.
3. Validar: calcular indicadores sobre la muestra observada, presentar gráficos con denominadores y comparar resultados con objetivos declarados previamente. Priorizar mejoras por impacto y esfuerzo y volver a probarlas. No presentar metas como resultados ni atribuir impacto social causal a una muestra breve.

La fecha de evaluación y la disponibilidad de participantes determinan el periodo real. No fabricar una retención de siete días si no se han observado siete días. El informe debe declarar el número de participantes, dispositivos, exclusiones, datos faltantes y sesgos de consentimiento y muestra.

## Instrumentación y privacidad

- Extender `services/mobile.py` y `FirebaseBridge.java` con eventos de nombre y parámetros permitidos. No aceptar objetos arbitrarios ni textos introducidos por personas.
- Aprovechar la elección independiente de estadísticas existente. Sin consentimiento no se inicia la medición de uso. Desactivarla detiene la colección y borra el registro local de evaluación pendiente; no debe prometer el borrado instantáneo de datos ya enviados a Google.
- Eventos de navegación lógica, acciones relevantes, resultados de guardado y errores clasificados por códigos fijos. Registrar intentos por separado de resultados; un clic no equivale a una mascota guardada o un pago aprobado.
- Cubrir Inicio, Mascotas, Chapa, Rutina, Salud, Cuenta, Avisos y Premium con nombres fijos. Evitar contar como visitas nuevas el refresco interno de la misma vista.
- Medir tiempo con reloj monotónico solo mientras la app está en primer plano. Considerar inactividad tras 30 segundos sin interacción; registrar duración activa y duración inactiva por pantalla. El umbral es una decisión técnica propuesta, no una definición dada por el profesor. No capturar coordenadas, teclas ni un mapa de calor.
- No enviar a Analytics nombres, correos, teléfonos, raza, historial sanitario, texto de errores, IDs de mascotas o cuentas, tokens de acceso, códigos QR o datos de tarjeta.
- La evaluación local usa códigos aleatorios y un esquema mínimo con fecha, evento, resultado y referencias locales necesarias para deduplicar. Es información seudónima; retener como máximo 30 días en el dispositivo, exportarla por elección explícita y mantenerla fuera de backups públicos y Git. Revocar estadísticas elimina todo el registro local de evaluación, conservando los datos funcionales de cuidados y pagos. La copia exportada y los datos ya enviados al proveedor tienen sus propios procedimientos de custodia y eliminación, que deben documentarse. La app funciona igual si se rechazan las estadísticas.
- Las pruebas en escritorio usan un adaptador local verificable. No fingir que esas pruebas demuestran recepción real en Firebase Android.

## KPIs propuestos

| Indicador | Definición y fuente | Uso |
| --- | --- | --- |
| Activación | Participantes nuevos de la cohorte que guardan su primera mascota / participantes nuevos observados. Eventos de inicio de prueba y primer guardado confirmado. Un dispositivo no equivale necesariamente a una persona. | Detectar fricción inicial. |
| Cumplimiento de cuidados | Ocurrencias programadas para el periodo que constan como completadas / ocurrencias programadas elegibles en ese periodo. Registro local persistente de programación y finalización, no cociente entre clics o tareas creadas. | Evaluar el uso del organizador de cuidados. |
| Éxito de guardado | Intentos de guardar con éxito persistente / intentos finalizados de guardar, desglosados por operación. Validación, fallo y abandono se muestran por separado. | Priorizar formularios y recuperación de errores. |
| Pago de prueba | Órdenes aprobadas / órdenes con resultado terminal, por identificador único de orden del servidor. Mostrar aprobadas, rechazadas, canceladas y pendientes por separado. | Validar el checkout; no representa ventas reales. |

Mostrar también tiempo activo, tiempo inactivo y número de interacciones como métricas descriptivas. No asumir que más tiempo o más clics significan mejor experiencia. Cada KPI tendrá fórmula, unidad, alcance, exclusiones, fuente, periodo, meta declarada antes de la prueba y decisión asociada. Un denominador cero se presenta como «Sin datos», no como 0 %.

Para activación, asignar un código aleatorio de participante y registrar una ficha consentida de inicio de la prueba. Deduplicar por ese código al consolidar dispositivos. No pedir nombre o correo ni interpretar el identificador de instalación como identidad de una persona.

Para cuidados, preservar la programación y la fecha prevista de cada ocurrencia antes de avanzar la repetición. Son elegibles las ocurrencias previstas en `[inicio, fin)` dentro de la cobertura observada, con corte de resultados en `fin`. Conservar las vencidas aunque después se edite o elimine la rutina; excluir cancelaciones anteriores a su vencimiento. El numerador incluye las completadas al corte; distinguir puntuales y tardías. No inferir el historial anterior al inicio del registro. Derivar las recurrencias desde los tramos de programación registrados para no perder las ocurrencias que el código actual salta al avanzar varios días. Registrar deshacer sin destruir la trazabilidad y calcular el último estado de cada ocurrencia. Una reimportación o sincronización no vuelve a contar la misma ocurrencia. Los cuidados sin fecha quedan fuera del porcentaje de cumplimiento programado y se muestran por separado.

## Resultados y entrega

Exportación local de la muestra consentida con filas mínimas y un resumen por periodo. Usar los informes de Firebase para uso y navegación, el registro de ocurrencias para cumplimiento y las órdenes del servidor para pagos. Las fuentes pueden tener distinta cobertura; no mezclar denominadores sin explicarlo.

Gráficos exportables para la presentación: activación, resultados de guardado, cuidados completados y pendientes, estados del checkout. No añadir un panel de administración o textos técnicos a las pantallas habituales de las personas usuarias. Preparar guía de recogida, diccionario de eventos, cálculo reproducible y plantilla de interpretación en `DOCUMENTATION.md` y documentación de evaluación. El informe final distingue resultados obtenidos de recomendaciones pendientes.

## Webpay Plus

- Mantener Supabase Auth, la propiedad de cada mascota y los periodos de ficha pública existentes.
- El servidor autenticado fija precio y moneda, crea una orden única y una transacción en el host de integración de Transbank. Las credenciales quedan en el servidor; nunca en la app.
- La app abre una URL propia de checkout. La web envía `token_ws` mediante formulario POST a Webpay. No pedir correo de comprador de Mercado Pago ni guardar tarjetas.
- El retorno del navegador no concede Premium. El servidor confirma o consulta el resultado con Transbank y valida estado, código de respuesta, importe, orden y sesión esperados antes de aplicar el periodo.
- La misma transacción solo otorga un periodo una vez, incluso con callbacks repetidos o consultas simultáneas. Bloquear por mascota y aplicar la extensión atómicamente: dos órdenes distintas aprobadas deben sumar dos meses y no sobrescribir la misma fecha. Restringir solicitudes por propietario y evitar crear otro pago cuando la creación anterior tiene resultado incierto.
- Un pago confirmado amplía un mes calendario desde la mayor fecha entre la vigencia actual y la confirmación del pago, con ajuste de fin de mes. Es una decisión técnica propuesta para conservar el tiempo ya pagado.
- Renovar exige otra acción explícita y otro pago; no hay renovación automática ni opción engañosa de cancelar futuros cobros inexistentes. Conservar las fechas ya confirmadas de la integración anterior. No cancelar suscripciones del proveedor anterior automáticamente: cualquier obligación existente requiere identificación y tratamiento explícito.
- UI: precio mensual, mascota elegida, fecha de vigencia, «Pagar con Webpay» o «Renovar Premium», estados comprensibles y aviso de pago de prueba antes de abrir el checkout. Mostrar la referencia de orden adecuada para soporte sin exponer tokens.
- Resolver aprobación, rechazo, anulación, timeout, regreso sin token y fallos de red. Permitir comprobar el estado sin volver a cobrar. Aislar pagos sandbox de métricas de ventas.
- Cambios alcanzan `services/subscription.py`, `screens/billing.py`, layouts y pruebas de Premium, la función de pagos y SQL del repositorio MiMascotaWeb, rutas web de checkout y retorno, documentación y configuración de despliegue.

## Comprobación y límites

Pruebas: consentimiento desactivado y revocado, esquema de eventos sin datos sensibles, acciones que fallan, duplicados, recurrencias y deshacer, periodo y zona horaria, actividad al suspender/reanudar, denominador cero; pagos de otro propietario, precio manipulado, callback repetido, respuesta incierta y resultado no aprobado. Probar el recorrido web y la persistencia local además de unidades.

Verificación real pendiente de implementación: recepción de eventos en Firebase DebugView en Android, recolección normal para informes, aprobación y rechazo en integración Webpay, retorno a la app y actualización de vigencia. DebugView demuestra envío técnico, no reemplaza la muestra de uso normal.

Los cambios se prepararán en ramas `feature/` para revisión y merge del usuario. No desplegar ni sustituir el APK de descarga hasta verificar esta versión. La rama de descarga 0.2.12 preparada antes de este alcance sigue pendiente de un APK con versión interna correcta; no debe mezclar estos cambios de producto con la publicación del binario anterior.

## Fuentes

- Rúbrica proporcionada: `C:/Users/Martin/Downloads/E4-rubrica.pdf`, ambas páginas.
- Diapositiva proporcionada: «Repaso 4: Analítica y Evaluación (MJV)».
- Firebase Analytics y precios: https://firebase.google.com/docs/analytics y https://firebase.google.com/pricing.
- DebugView: https://firebase.google.com/docs/analytics/debugview.
- Transbank: https://github.com/TransbankDevelopers/transbank-developers-docs/blob/master/documentacion/webpay/README.md.

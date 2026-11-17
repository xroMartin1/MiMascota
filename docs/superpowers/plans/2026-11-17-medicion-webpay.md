# MJV y Webpay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. El usuario aprobó el diseño y pidió implementarlo; no repetir la aprobación.

**Goal:** medición gratuita verificable y Webpay Plus sandbox con renovación mensual manual.
**Architecture:** SDK Firebase existente + registro local consentido de evaluación; órdenes de pago y confirmación solo en servidor Supabase, web intermediaria POST y cliente Kivy.
**Tech Stack:** Python/unittest, Java Firebase, Next.js/TypeScript, Deno, Postgres.
**Spec:** ../specs/2026-11-17-medicion-mjv-transbank-design.md

## Global Constraints
- Ramas feature/, nunca merge a main ni despliegue automático en este trabajo.
- $3.990 CLP por mes calendario por mascota, sandbox, renovación manual.
- Consentimiento opcional, sin PII en eventos; retención local de 30 días.
- No mezclar la publicación del APK anterior con este código.

## Review Focus
- Cuidados recurrentes omitidos, reprogramados o deshechos no deben inflar el cumplimiento.
- Dos pagos distintos concurrentes suman dos meses; el mismo pago no se aplica dos veces.
- Fallos de medición no bloquean el cuidado ni la persistencia.
- Interrupción del navegador o proceso deja un pago consultable sin duplicarlo.
- Revocar estadísticas elimina evaluación local, sin tocar cuidados ni pagos funcionales.

### Task 1: Registro de medición y Firebase
Files: services/measurement.py, services/mobile.py, android/src/org/mimascota/FirebaseBridge.java, tests/test_measurement.py, tests/test_mobile_auth.py.
Interfaces: Measurement(path, sender=None); configure(enabled, data=None), event(name, **params), screen(name), touch(), pause(), resume(), observe(data), care_completed(task_id, due_at, undo=False), export(path), summary(start,end). Los adaptadores admiten nombres y parámetros permitidos; ningún texto libre se envía a Firebase.
- [x] Escribir y ejecutar pruebas rojas de consentimiento, validación, retención, reloj, programación/repetición, cancelación, deshacer y duplicados.
- [x] Implementar registro atómico mínimo y adaptador SDK, incluyendo cohortes y activación verificables.
- [x] Ejecutar pruebas propias y suite Python; revisar esquema de privacidad.

### Task 2: Órdenes Webpay y web
Files en MiMascotaWeb: nueva función webpay-payments, SQL incremental y verificador, rutas pago/webpay y pago/resultado, pruebas Deno/Playwright, documentación.
Interface: POST autenticado webpay-payments {action:'create'|'status',pet_id}; respuesta {provider:'webpay',test_mode:true,amount:3990,currency:'CLP',state:'none'|'creating'|'pending'|'active'|'rejected'|'cancelled'|'expired',paid_until,checkout_url,order_id}; checkout_url del propio sitio /pago/webpay?checkout=capability. Servidor procesa POST público de callback con token_ws, sin confiar en datos del navegador. Precio y periodos solo en servidor.
- [x] Escribir pruebas de límites de confianza, proveedor y reintentos.
- [x] Crear tabla de órdenes privada, RPC service-only con bloqueo e idempotencia, sin modificar periodos previos.
- [x] Implementar integración REST sandbox y rutas POST web con confirmación del servidor; preservar integración anterior sin permitir nuevos cobros desde la app.
- [x] Verificar Deno, SQL local si herramientas disponibles, lint, compilación y checkout web con proveedor simulado.

### Task 3: Integración Kivy y evidencia
Files: services/subscription.py, screens/billing.py, screens/billing.kv, screens/home.py, screens/features.py, main.py, tools/report_measurement.py, tests y scripts UI afectados.
- [x] Ajustar tests del contrato para Webpay antes del cliente. Verificar host propio y estados sin solicitar correo o cancelación de renovación automática.
- [x] Instrumentar acciones después de persistencia, navegación, actividad y ciclo de vida; conectar consentimiento/exportación con controles existentes.
- [x] Crear informe reproducible con JSON/CSV y gráficos HTML exportables, sin inventar datos ni añadir un panel técnico al flujo habitual.
- [x] Verificar KPIs de fixtures y UI de pago/consentimiento/exportación y errores.

### Task 4: Revisión y entrega
Files: DOCUMENTATION.md, MEDICION-MJV.md, PAGOS-DE-PRUEBA.md, README.md, ANDROID-SERVICIOS.md.
- [x] Documentar diccionario de eventos, fórmulas, protocolo MJV, periodo/muestra/metas por completar y límites.
- [x] Revisión independiente de pagos y medición; resolver hallazgos materiales.
- [x] Ejecutar suite Python, UI afectada y pruebas web; registrar checks reales y pendientes Android/servicios.
- [x] Commits/push exclusivamente a ramas de trabajo, sin merge ni publicación del APK; verificar remoto y estado.

## Ledger
- Aprobación: usuario «Aprobar e implementar», 2026-11-17.
- Ruling: dos implementadores independientes para motor de medición y backend; integración de app y revisión final por coordinador. No compartir archivos editables entre tareas.
- Ruling: no desplegar servicios remotos sin comprobar proyecto y secretos de servidor; entregar código y pasos si el proyecto conectado no corresponde.

## Evidencia y decisiones de cierre
- App: 129 pruebas unitarias verdes; nueve scripts UI afectados verdes, con consentimiento/exportación/Premium a 390 y 320 px. El script de signup requiere MIMASCOTA_PREVIEW_DIR y se repitió con esa variable.
- Web: 25 pruebas Deno, cuatro checkout Playwright y cuatro de descarga/portada, SQL real PGlite secuencial, lint/TypeScript/build webpack verdes. No se ejecutó el esquema remoto completo ni contención entre conexiones.
- Revisión independiente corrigió revocación con fallo de disco, referencias compartidas entre dispositivos, cambio de cohorte, DST, formato UUID.HMAC y selección explícita de órdenes por cohorte.
- Seguridad: Next.js y eslint-config-next actualizados a 16.4.6; auditoría runtime de producción sin avisos. Dieciséis avisos previos de herramientas de desarrollo permanecen documentados.
- Ruling: mantener API MP histórica por compatibilidad con APK previos, documentar que conserva create mientras existan credenciales; el cliente nuevo usa solo Webpay. Retirar esa API requiere revisar suscripciones anteriores.
- Ruling: observaciones de participantes, metas y periodo de evaluación real quedan a cargo del equipo; las pruebas y el informe visual de fixtures no se presentan como resultados reales.
- Pendiente externo: desplegar proyecto correcto, validar DebugView en Android y sandbox HTTPS real, compilar nuevo APK antes de actualizar descarga. Ningún despliegue se realizó.

# Mi Mascota: documentación técnica y evaluación

Aplicación Python/Kivy para perfiles, cuidados, salud y chapa QR de mascotas, con persistencia local y cuenta Supabase opcional. Este documento acompaña el código de la rama de medición MJV y Webpay; no declara un despliegue ni resultados reales de participantes.

## Arquitectura que se puede mostrar en la defensa

- Vistas: layouts declarativos `screens/*.kv` y componentes `screens/views.py`.
- Controladores: `screens/home.py` coordina navegación; mixins de funcionalidades en `screens/features.py`, `screens/ux.py`, `screens/measurement.py`, `screens/billing.py` y módulos especializados.
- Modelo y servicios: `services/store.py` valida y guarda de forma atómica; servicios separados para nube, agenda, pagos, recordatorios y medición. La lógica y los datos se prueban sin abrir una pantalla.
- Integración nativa: Java Firebase a través de `services/mobile.py` y Pyjnius. La app sigue funcionando localmente si el SDK está ausente o se rechaza medición.
- Servidor: Supabase Auth y funciones con propiedad de datos. Webpay crea y confirma órdenes en el servidor; Next.js aloja el formulario POST y el retorno. Ningún secreto de cobro se distribuye en el APK.

No se presenta como MVC estricto: existen coordinadores grandes y mixins. La separación comprobable es entre layouts, flujos y servicios independientes. Para explicar POO se pueden recorrer HomeScreen y sus clases de funciones, LocalStore, Measurement y Subscription con sus responsabilidades y colaboraciones concretas.

## Demostración operativa

1. Abrir en Android o escritorio; registrar una mascota y un cuidado. Cerrar y reabrir para mostrar persistencia real.
2. Iniciar sesión y mostrar propiedad de datos, estados de error y funcionamiento sin conexión dentro de sus límites.
3. Abrir Privacidad y estadísticas; mostrar opt-in y el rechazo sin pérdida de funciones.
4. Registrar una prueba consentida y una acción. Exportar y enseñar el evento que alimenta el KPI y su fórmula. Mostrar datos de prueba como tales.
5. Abrir Premium y pagar solo en sandbox, una vez desplegado el backend de esta rama. Un rechazo o cierre no debe activar Premium; una aprobación se confirma en servidor y extiende una vez.

## MJV, KPI e informe final

La metodología completa está en [MEDICION-MJV.md](MEDICION-MJV.md): protocolo previo, diccionario, fórmulas, cohortes, periodo y comandos reproducibles. Los gráficos se generan desde exportaciones reales y se acompañan con observaciones de uso; no se crean porcentajes para rellenar la presentación.

La rúbrica exige un informe final con hallazgos y propuestas. Todavía debe completarse con la muestra y los resultados recogidos por el equipo. Plantilla de contenido:

1. Problema y evidencia del diagnóstico realizado con personas usuarias; referenciar entrevistas u observaciones reales.
2. Solución y relación de cada función con el problema.
3. MJV: preguntas, metas previas, periodo, muestra, instrumento y fuentes.
4. Resultados: gráficos con numeradores/denominadores, interpretación y límites.
5. Mejoras priorizadas por impacto y esfuerzo, con forma de validar cada cambio.
6. Reflexión social y ética: privacidad, consentimiento, accesibilidad, sesgos y límites de lo demostrado. Declarar el uso de IA según [USO_IA.md](USO_IA.md).

## Comprobaciones

```bash
python -m unittest discover -s tests
python tools/check_measurement_ui.py
python tools/check_subscription_ui.py
```

Usar el entorno de desarrollo con dependencias instaladas; los scripts UI requieren sesión gráfica. El verificador del APK comprueba contenido y configuración pública, no sustituye instalarlo en un teléfono. Las comprobaciones automatizadas usan fixtures, sin publicar datos ni realizar cobros.

## Límites antes de distribución

- La nueva app y el nuevo backend/web deben integrarse y desplegarse juntos; el endpoint anterior de Mercado Pago no sirve a este cliente.
- Falta la prueba física Android de Analytics/DebugView y del retorno del sandbox con la firma de distribución prevista.
- No se compiló un APK de esta rama en este equipo. `buildozer.spec` declara 0.2.12 para la próxima compilación, no para renombrar un binario antiguo.
- La transacción se conserva y se puede consultar si se interrumpe el navegador. Los pasos operativos y límites están en [PAGOS-DE-PRUEBA.md](PAGOS-DE-PRUEBA.md).
- Las métricas no prueban que una mascota perdida haya vuelto a casa ni beneficios sanitarios. Evitar atribuciones que la muestra y el instrumento no midan.

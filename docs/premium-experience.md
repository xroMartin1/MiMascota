# Experiencia Premium

Alcance solicitado: confirmación bonita de pago con la mascota, chapa centrada con nombre dinámico, sin referencia de pago visible, contorno Premium suave en el perfil y algunas razas adicionales. Precio resumido en perfil: `$3.990 CLP / mes`.

Decisión del usuario: chapa física incluida en la primera compra; renovaciones mantienen el servicio. No inventar un estado de envío ni una dirección o plazo de entrega. El checkout continúa siendo sandbox.

## Implementación

- [x] Componentes Kivy: `screens/premium.py` (chapa personalizable, contorno animado, celebración), `screens/billing.kv`; registro de componentes antes de cargar KV. Animaciones cortas o lentas, sin bucles al cerrar, suspender o desactivar movimiento.
- [x] Estado funcional: servicio `services/premium.py`, cache por cuenta con vigencia confirmada y pagos ya celebrados. Solo respuestas del servidor otorgan el distintivo; no concede permisos en el servidor. Un pago nuevo se celebra una vez, no al refrescar. Una renovación se reconoce por orden y nueva vigencia; un fallo no revoca el tiempo ya pagado.
- [x] Integración: `screens/billing.py` procesa resultados y abre bienvenida o detalle; `home.kv` usa botón Premium, inicio/restauración/reanudación refrescan el estado sin bloquear cuidados; logout/cambio de cuenta limpia el distintivo. No recrear solicitudes en bucle.
- [x] Imagen: placa frontal sin texto fijo y cuatro retratos (Beagle, Dachshund, Husky y Ragdoll), transparentes y optimizados, con catálogo y compatibilidad de datos previos.
- [x] Pruebas: vigencia y duplicados, cambio de propietario, renovación, errores/offline, textos y nombres largos, escritorio 390/320, movimiento reducido y limpieza de animaciones. Revisar capturas reales y fuente de verdad de pago.
- [x] Documentación de beneficios y de evaluación sin referencia de orden en UI. Commit y push en `feature/premium-experience`, sin modificar main o desplegar.

## Interfaces

`PremiumAccountButton(ViewAction)` expone `premium` y `motion_active`. `PersonalTag(Widget)` expone `name` y `source`. `PremiumWelcome` recibe name/kind/breed/date/renewal en context y ofrece animación de entrada cancelable. El controlador añade su CTA y decide cuándo mostrarlo.

El grabado del nombre se dibuja en la UI sobre una imagen de placa vacía para no generar una imagen por mascota. El QR real sigue en Chapa: la representación de producto no pretende ser el QR escaneable de la mascota.

## Comprobación

148 pruebas unitarias pasan, incluidos pagos nuevos, duplicados, caducidad, cambio de cuenta y respuesta antigua de fondo. Recorridos Kivy comprobados a 390/320 px y 480 px de alto, con movimiento reducido y cierre de animaciones. La confirmación reconsulta al volver al foco desde el navegador en PC; en Android conserva el retorno de ciclo de vida. La celebración usa el retrato normal de la mascota por raza, con un pequeño salto, corazones y huellas: no cambia su identidad ni añade una mascota genérica.

La primera compra incluye la chapa física como política del producto. La bienvenida no afirma un envío de esta orden ni deduce que una renovación incluya otra chapa. No hay gestión logística ni pruebas físicas de Android de esta versión. La siguiente versión con correcciones de compartir, navegación y Premium es 0.2.16; ver `APP-0.2.16.md`.

La eliminación de una mascota con Premium vigente se detiene con una explicación de su fecha de término y de que el plan no se transfiere. En cuentas conectadas, antes de mostrar la confirmación de eliminación se comprueba la chapa y su plan en el servidor, incluso si falta la caché local; si no se puede verificar, se conservan los datos y se pide recuperar la conexión. El invitado puede seguir eliminando mascotas sin conexión. Los resultados y confirmaciones anteriores se descartan si cambia la cuenta o el archivo de datos. Esta protección pertenece al flujo de la app: no impide que otro cliente modifique directamente la copia del servidor.

Abrir Premium sin chapa web muestra una instrucción y lleva a la pantalla Chapa, que consulta la prueba de la cuenta. No emite un QR ni reinicia automáticamente la prueba. Registrar otra mascota sigue siendo gratuito; la prueba única por cuenta y los planes por mascota conservan sus reglas actuales. Los distintivos del detalle Premium identifican la continuidad de la ficha y del mismo QR; la chapa física se distingue como beneficio de la primera compra.

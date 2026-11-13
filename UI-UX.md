# Revisión de inicio y ventanas · 0.2.10

El inicio presenta primero los perfiles de mascotas (hasta tres; el resto se consulta desde «Ver todas mis mascotas»), después los cuidados pendientes y luego un acceso al QR. Cada fila abre el perfil o el detalle correspondiente. Sin mascotas, la primera acción es añadir una, sin pedir registro.

Se retiraron el badge «Tu espacio», el eslogan de portada, la promoción grande del QR y los contadores con ceros. Se mantiene el fondo blanco, los colores de marca, los retratos existentes y la navegación. El consejo remoto sigue disponible para demostrar la configuración remota del curso.

Las ventanas cortas se ajustan al contenido; los formularios conservan su altura y desplazamiento. El cálculo de altura espera al siguiente ciclo de Kivy para medir los títulos después de ajustar sus líneas. Los textos largos de las filas pueden ocupar varias líneas y los controles de cierre tienen 48 dp. «Chapa y suscripción» se encuentra directamente en Cuenta.

## Referencias consultadas

- [Pet Health+](https://pethealthplus.app/): separación entre cuidados del día, próximos registros y perfil de la mascota.
- [11pets](https://www.11pets.com/en/feature): información de salud y cuidados organizada por animal.
- [Bearable](https://bearable.app/support/tips/the-bearable-starter-pack/): priorizar en el inicio la información relevante para la persona.
- Vault My Mind del equipo: Diseño sin slop, Escritura para interfaces y Pulir interacciones. Se aplicaron las pautas de quitar insignias redundantes, nombrar acciones concretas y comprobar el resultado a tamaño real.

Estas referencias orientan decisiones de diseño; no constituyen una investigación de usuarios ni se copian sus pantallas.

## Verificación

`tools/check_home_layout.py` usa registros ficticios y temporales: sin mascotas, con perro y gato, nombres largos, anchos de 390 y 320 píxeles, notificaciones, ajustes y formulario de mascota. Las comprobaciones de escritorio no sustituyen la revisión final en un teléfono Android.

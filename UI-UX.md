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

## Continuación · 0.2.11

Mascotas reutiliza las filas con retratos del inicio; peso, microchip y acciones se consultan desde el perfil. Se conserva un acceso al QR en la lista y en la navegación. Rutina presenta las tareas antes de la ilustración y mantiene el botón Hecho. Los títulos y fechas de cuidados admiten varias líneas. Salud distingue registros guardados de cuidados pendientes sin inferir un estado médico. `tools/check_sections.py` comprueba estas pantallas en 390 y 320 píxeles con datos temporales.

## Dirección cálida y expresiva · 16 de noviembre de 2026

Se conserva la marca y la navegación. El fondo pasa a crema #FAF7F2; las superficies combinan blanco, menta #E2F0EA y coral suave. El petróleo #103D49 ancla acciones y Chapa; coral #F28B74 y lima #DAEFA0 aportan contraste. Los retratos existentes tienen más presencia, también en Salud. El QR real permanece cuadrado, estable y sobre blanco.

Las pulsaciones responden con una tinta inmediata que se retira en 120 ms; las páginas cambian en 200 ms y los diálogos entran con opacidad y escala breve de 97% a 100%. Se consulta la preferencia de animaciones tanto de Android como de Windows. No se añaden dependencias de animación.

Los formularios cortos se ajustan al contenido, recalculan su altura al cambiar el tamaño de ventana y conservan el scroll para contenido largo. La hora dispone de ancho propio a 320 px. Las conversaciones cortas empiezan arriba; las largas muestran la zona de respuesta. Un callback pendiente de conversación no desplaza otra página.

`tools/check_design_ui.py` usa datos temporales sin cuenta real: captura las seis páginas a 390/320 px y comprueba hora completa, conversación corta/larga, cambios rápidos de página, formularios al reducir altura, detalles largos a 320×560, fallos de guardado y movimiento reducido/interrumpido. Las capturas están en `previews/design-after`. Las pruebas de escritorio no sustituyen teclado, TalkBack y fluidez en Android físico.

### Ajuste de color y mensajes
Las acciones principales usan petróleo con texto blanco; las secundarias, menta o lima con texto oscuro. Los tonos rojizos se reservan para errores y acciones destructivas; las superficies decorativas cálidas pasan a arena #F3EDDA. Texto e icono de los botones horizontales se centran por su altura visible. El consejo conserva su origen remoto, sin mostrar estado técnico de actualización o caché. El texto remoto de prueba debe sustituirse en el proyecto de MiMascota cuando se disponga de acceso: la conexión Supabase disponible pertenece a otro proyecto.

## Composición editorial · 16 de noviembre de 2026

Se amplía el lenguaje de la web a la app mediante retratos ilustrados sobre arcos y composiciones de mascota y chapa. Inicio destaca el próximo cuidado; Rutina presenta una agenda de horas y fechas con sus acciones y sin banner de spa. Cuenta agrupa opciones; Avisos distingue los mensajes nuevos con una marca lateral y un estado vacío ilustrado.

Salud integra la selección dentro de la ficha: nombre único, retrato, peso e historial separados, y Compartir PDF. Cambiar mascota solo aparece con varias; el diálogo usa identificadores internos y admite nombres repetidos. El contenido se desplaza al faltar altura. Los perfiles también conservan acceso desplazable a todas sus acciones.

Se verifican las especies de los retratos, selección con nombres repetidos, cancelación, exportación, nombres largos y completar/reabrir cuidados desde la agenda. El QR activo mantiene su superficie blanca estable. Capturas en previews/editorial y previews/design-after; cuenta/avisos en previews/ux. No se modifican servicios, datos ni la web.

### Vista de la chapa de la web
La introducción de Chapa usa `assets/chapa-web-3d.png`, una vista frontal renderizada del modelo público `https://mi-mascota-web.vercel.app/models/chapa-circular.glb`. Se muestra como «Chapa de ejemplo»: es una imagen estática local con transparencia, sin visor web ni dependencias 3D en la app. El render y el modelo de referencia quedan en `previews/chapa-web`; Blender se utilizó solo para generar el recurso. El QR personal activo conserva su representación separada y estable.

La vista de ejemplo muestra el frente y el reverso de la chapa uno junto al otro, con las etiquetas Frente/Reverso. El reverso se renderiza del mismo modelo en assets/chapa-web-3d-reverso.png; ambos son recursos estáticos locales.

### Respuesta al uso y reintentos

Completar un cuidado confirma el guardado con un cambio breve de escala e icono; cambiar de mascota revela su contenido en 180 ms. Ambas transiciones respetan movimiento reducido. Tocar cualquiera de las dos vistas de la chapa abre una ampliación con acceso al otro lado; el QR personal sigue separado.

Los formularios remotos conservan los campos abiertos durante la petición, muestran «Procesando…» y permiten reintentar con el texto intacto tras un error. Un fallo de guardado local también conserva el formulario. Las ediciones recuperan el registro vigente tras una restauración local y los reintentos de respuesta conservan su identificador para evitar duplicados. `tools/check_micro_ui.py` verifica estos recorridos con servicios simulados y archivos temporales; captura el error y la chapa ampliada en `previews/micro`.

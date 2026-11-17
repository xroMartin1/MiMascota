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

## Premium y perfiles por raza · 16 de noviembre de 2026

Premium tiene una tarjeta propia en Cuenta y acceso contextual desde Chapa. Su diálogo separa precio, beneficios y estado confirmado; la acción principal permanece fuera del scroll. Las instrucciones del entorno de prueba se muestran antes de abrir Mercado Pago. Se conserva la validación de servidor, el precio mensual por mascota y la integración exclusivamente de prueba.

Las superficies blancas mantienen bordes opcionales y las fichas de mascotas ganan retratos más grandes, menta y lavanda. Inicio usa un acceso práctico a Chapa sin el hueso ni eslóganes. El encabezado muestra solo la marca. Rutina recupera la ilustración de mascotas en un banner compacto. Se sustituyen los puntos intermedios por texto separado con comas o líneas.

El catálogo ofrece seis razas caninas y cinco felinas, además de Mestizo, Otra raza y Sin registrar. Las razas anteriores se conservan al editar. La especie controla el selector de razas; los retratos corresponden a la especie y raza en Inicio, Mascotas, Salud, perfiles y selectores. Son ilustraciones de referencia, no fotos de los animales del usuario. Los doce PNG de avatares se optimizan a 256 px y ocupan unos 497 KB en total. Los originales anteriores y la hoja de control quedan en previews/avatars-source; los diez retratos nuevos se generaron con imagegen.

Las edades numéricas se presentan como «1 año» o «3 años» sin cambiar el dato guardado; se conservan textos como «6 meses». El campo de una línea centra texto y placeholder por su altura real, y restaura el color de texto después de dibujar el borde. Las capturas y comprobaciones de recorrido quedan en tools/check_premium_design_ui.py y tools/check_subscription_ui.py. Las pruebas locales no sustituyen la validación de APK, teclado y accesibilidad en Android físico.

### Dos superficies y movimiento al interactuar

Los retratos eliminan el círculo y el fondo de la ilustración: quedan la tarjeta pastel y el arco blanco. Se editaron los doce avatares con imagegen integrado conservando su identidad; los PNG RGBA finales de 256 px, optimizados sin pérdida, ocupan 1.09 MB en total. Los originales previos, la hoja de control y los prompts exactos con sus rutas de entrada/salida quedan en previews/portrait-arches/source, cutouts-catalog.png y generation.json dentro de previews/portrait-arches. Conejo, Ave, Pez, Reptil y Hámster usan iconos propios; las especies desconocidas usan una huella sin disco decorativo.

Las tarjetas de mascota y Premium comprimen su escala a 98.5% en 90 ms y vuelven en 160 ms. El formulario de mascota muestra un retrato previo que cambia al elegir especie o raza, con un fundido de 140 ms que termina siempre en la última selección. Los desplegables incorporan una flecha que gira en 150 ms y áreas de 48 dp. No se anima el QR escaneable ni se añaden movimientos permanentes; con movimiento reducido se aplican los estados finales directamente.

El formulario cierra sus desplegables y cancela las animaciones de flechas y vista previa al descartarse, incluidas las ideas rápidas. tools/check_portrait_motion_ui.py verifica toque único, arrastre sin abrir ficha, presión y retirada de tarjetas, cambios rápidos de raza, cierre del modal y movimiento reducido con el bucle real de Kivy. Las capturas quedan en previews/portrait-arches; las pruebas de assets comprueban tamaño y transparencia real. No se compila APK ni se sustituye la validación en Android físico.

La revisión final de textos elimina referencias visibles a servidores, Firebase, archivos internos y mockups, además de explicaciones repetidas de acceso, retrato y estados Premium. El estado de las copias se consulta dentro de Datos y respaldos. Se conservan fechas, precio, condiciones del pago de prueba y consecuencias de privacidad, borrado y restauración. El consejo sigue siendo remoto; el marcador técnico «Mensaje modificado vía Remote Config» se rechaza y conserva el último consejo válido o el consejo inicial. Los errores y los avisos usan instrucciones breves en lenguaje cotidiano.

### Ficha protagonista, agenda diaria e historia

El perfil reúne nombre, retrato grande, raza, edad, peso y próximo cuidado, con acceso a Salud, Chapa y edición. La agenda conserva todos los cuidados y los agrupa en Ahora, Más tarde, Sin fecha y Completados. El progreso de hoy cuenta identificadores únicos con finalizaciones guardadas y pendientes con fecha de hoy; las repeticiones mantienen su próximo turno y muestran su finalización de hoy como registro de consulta. Eliminar un cuidado conserva su historial y progreso ya registrado; los cuidados sin fecha y vencidos de días previos no inventan actividad de hoy.

Salud muestra los tres registros más recientes y el historial completo conserva edición y eliminación. Los empates de minuto muestran primero el último registro añadido. La cronología identifica el tipo de registro y no deduce estados médicos ni cambios de peso sin datos. La chapa de ejemplo gira al tocar la imagen o su botón, con bloqueo durante el giro, movimiento reducido y cancelación al cerrar. El QR personal no se anima.

screens/theme.py centraliza la paleta, tipografía base, separación y radios principales de los KV y controles compartidos. Los cambios no añaden dependencias ni modifican el formato guardado. tools/check_story_ui.py captura perfil, agenda, Salud e historial a 390/320 px y verifica acciones, recurrencia, progreso, giro y cancelación; tests/test_agenda.py comprueba fechas, reapertura y eliminación. Capturas en previews/story. Sigue pendiente compilar y validar en Android físico.

### Repaso final · 17 de noviembre de 2026

Se revisaron las pantallas principales, perfiles, formularios, mensajes, acceso, chapa, estados Premium, copias y recordatorios en escritorio a 390/320 px y con altura reducida. Se corrigió la selección de navegación al abrir Chapa desde un perfil: ahora marca Chapa, aunque el acceso parta de Inicio o Mascotas. El banner de Rutina se adapta a la altura de ventana para dejar más espacio a la agenda.

Las comprobaciones históricas de mensajes y publicación de QR se actualizaron a las páginas y acciones actuales; el consejo remoto se prueba con una respuesta simulada válida, sin depender del marcador de diagnóstico del proyecto remoto. Los 18 recorridos de interfaz y las 95 pruebas unitarias pasan; logs y capturas de repaso en previews/final-review. La validación no incluye APK, Android físico ni pagos reales.

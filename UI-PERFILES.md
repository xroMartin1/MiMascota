# Ajustes de interfaz · perfiles de mascotas

Se conservan el fondo blanco, el azul petróleo y el verde lima del proyecto. Las guías del vault My Mind utilizadas fueron Diseño sin slop, Escritura para interfaces y Pulir interacciones: se aplicaron para priorizar acciones claras, revisar textos en contexto y comprobar las pantallas pequeñas.

## Cambios

- Retratos originales generados para perro y gato, con referencia visual en la ilustración de cuidados. Archivos: `assets/avatars/perro.png` y `assets/avatars/gato.png`.
- `PetAvatar` muestra los retratos dentro de un círculo, tanto en la lista como en el perfil. Para otras especies y archivos ausentes se conserva el dibujo alternativo existente.
- Botón «Ver chapa QR» con texto estable, para evitar recortes por nombres largos. «Ver perfil» tiene mayor énfasis visual.
- «Mis mascotas» y concordancia de singular/plural en mascotas y cuidados.
- Controles de cuenta y campana de 48 dp, con el título ajustado al ancho compacto.
- Cuando está disponible Google, «Crear cuenta» tiene menor énfasis para evitar dos acciones principales compitiendo.

## Comprobación

Se revisaron las seis pantallas principales a 320 y 390 píxeles, incluyendo nombres largos. Se comprobó la selección de retratos y el dibujo alternativo, además de los recorridos existentes de cuenta y mensajes QR. Las capturas usan datos sintéticos; no contienen cuentas reales.

La preparación de Mercado Pago se describe por separado en `PAGOS-DE-PRUEBA.md`. Los recordatorios y su prueba física quedan para la siguiente etapa.

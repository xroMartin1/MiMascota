# Declaración de uso de inteligencia artificial

Este documento describe el uso de inteligencia artificial durante el desarrollo de Mi Mascota, las decisiones del equipo y su reflexión sobre el proceso.

## 1. IA usada

Se utilizó Codex, asistente de programación de OpenAI, para apoyar el desarrollo y la documentación. También se utilizó ChatGPT para generar imágenes para la interfaz a partir de prompts.

## 2. Modelo

Se utilizaron modelos de OpenAI a través de Codex; la conversación incluye una sesión identificada como GPT-6. No se dispone de un registro completo de las versiones usadas en todas las sesiones. Para las imágenes se utilizó ChatGPT; no se confirmó el nombre ni la versión del modelo de generación de imágenes.

## 3. Prompts realizados

Estos ejemplos resumen fielmente solicitudes que guiaron decisiones del proyecto; no son una transcripción completa de las conversaciones:

1. **Concepto e interfaz:** «Quiero que cambies la UI actual a la de las imágenes que te envié». Se describió la app para dueños de mascotas, con perfiles, información veterinaria, recordatorios y QR, manteniendo Kivy y KivyMD por la pauta del curso.
2. **Diseño e identidad:** se pidió renombrar la app a Mi Mascota y hacer la interfaz menos genérica, con un fondo blanco y una presentación que destacara la chapa QR. Se compartieron referencias visuales y se sugirió inspiración en Codegrid.
3. **Textos y navegación:** se señaló que «pendientes» y «vencidos» podían interpretarse como si se refirieran a las mascotas, y se pidió corregir el texto y revisar la alineación de la barra de navegación.
4. **Imágenes:** se solicitaron prompts para una ilustración de cuidados, una chapa con forma de hueso y sus vistas realistas de frente y atrás. Al recibir una imagen demasiado realista para Inicio, se solicitó una alternativa más ilustrada.
5. **Facilidad de uso:** se pidió mejorar el formulario de mascotas con opciones para especie y microchip, además de otras mejoras que hicieran más rápida y clara la interacción.
6. **Cuenta y funcionamiento sin registro:** se pidió que las funciones disponibles sin cuenta guardaran datos localmente, y que las funciones de cuenta y sincronización utilizaran Supabase. Después se solicitaron mejoras para conservar la sesión, simplificar la sincronización, recuperar la contraseña e iniciar sesión con Google.
7. **Problemas técnicos:** se informó que la aplicación aparecía en blanco tanto en PC como en Android y se pidió investigar la causa. También se pidió corregir la superposición de la interfaz con las barras del sistema del teléfono.
8. **Notificaciones y configuración remota:** se pidió explicar una notificación local útil y, para la evaluación, añadir un consejo de cuidado obtenido desde una fuente remota que se muestre en Inicio y conserve una alternativa cuando no haya conexión.
9. **Entrega y defensa:** se solicitó compilar el APK, publicarlo en la página de descarga y preparar una guía que explique la organización del código, los servicios y preguntas que podrían aparecer durante la evaluación.

## 4. Outputs

La IA entregó propuestas de código Python, KV, SQL y Java, pruebas, diagnósticos, documentación, explicaciones y prompts de imágenes. Se incorporaron partes para la interfaz, persistencia, autenticación, QR, avisos, sincronización y consejo remoto. Algunas propuestas visuales se revisaron: una imagen de chapa demasiado realista se consideró inadecuada para la ilustración de Inicio, y se pidieron alternativas. Los detalles de otros descartes deben ser confirmados por quienes trabajaron en ellos.

## 5. Ajustes

Al comienzo del proyecto realizamos ajustes nosotros mismos. Más adelante utilizamos principalmente la IA para implementar los cambios y correcciones: le indicábamos qué queríamos cambiar, revisábamos el resultado y le pedíamos nuevas modificaciones cuando algo no nos convencía o no funcionaba como esperábamos.

Por ejemplo, pedimos pasar del fondo crema a blanco, aclarar los textos sobre cuidados pendientes, corregir la alineación de la navegación, facilitar los formularios y cambiar el diseño de la chapa. También informamos problemas observados al probar la app, como la pantalla blanca y la pérdida de sesión, para que la IA investigara y aplicara correcciones.

Por lo tanto, los ajustes posteriores no se presentan como cambios de código escritos manualmente por cada integrante: nuestras aportaciones consistieron en decidir qué cambiar, dar indicaciones y revisar los resultados. Para la defensa debemos estudiar y comprender el código que finalmente se entrega.

## 6. Reflexión en el uso de IA

La IA nos ayudó bastante y nos ahorró tiempo, porque pudimos avanzar sin tener que escribir cada línea de código desde cero. Aun así, tuvimos que revisar las propuestas y decidir si realmente se ajustaban a lo que necesitaba nuestra aplicación.

Una de las partes que más nos costó fue revisar el diseño: buscar cómo hacerlo correctamente y lograr que las pantallas y sus funciones se entendieran para una persona que usara la app. Por eso fuimos pidiendo cambios en los colores, los textos y los formularios a medida que probábamos el resultado.

Aprendimos que el trabajo en equipo es importante para compartir ideas, revisar las decisiones y entender lo que se presenta. La IA nos permitió avanzar más rápido, pero también vimos la importancia de comprobar lo que entrega y conocer el código para poder explicarlo. Sin su ayuda, el desarrollo nos habría tomado mucho más tiempo.

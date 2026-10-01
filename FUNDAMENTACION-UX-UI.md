# Fundamentación UX/UI — Mi Mascota

**Evidencia:** [captura de resultados agregados](assets/evidencia-encuesta-ux.png) y aplicación actual. Se separan datos observados de decisiones e hipótesis de diseño.

## a) Metodología de investigación

Se documentó **una encuesta digital con 13 respuestas**. El instrumento muestra tres preguntas: edad y frecuencia de uso móvil (selección única), y atributos valorados en una app nueva (selección múltiple). **Entrevistas documentadas: 0**; no hay citas textuales. Respondieron 9 personas de 18–24 años, 2 menores de 18 y 2 de 45–54. No consta el reclutamiento ni si tienen mascotas: la muestra orienta la interfaz, pero no valida necesidades de propietarios.

## b) Resultados principales

| Pregunta | Evidencia de la encuesta (n = 13) | Lectura prudente |
|---|---|---|
| Edad | 18–24: **9/13 (69,2 %)**; menores de 18: **2/13 (15,4 %)**; 45–54: **2/13 (15,4 %)**. | Evitar diseñar solo para jóvenes. |
| Uso de apps móviles | Varias veces al día: **11/13 (84,6 %)**; una vez al día: **1/13 (7,7 %)**; rara vez: **1/13 (7,7 %)**. | Facilitar consultas breves; no prueba uso diario de esta app. |
| Valor al probar una app | Atractiva: **11/13 (84,6 %)**; fácil: **10/13 (76,9 %)**; rápida: **7/13 (53,8 %)**; simple: **4/13 (30,8 %)**; muchas funciones: **4/13 (30,8 %)**. | Predominan aspecto y facilidad. Era selección múltiple: no suman 13. |

## c) Matriz hallazgo → decisión de diseño

| Hallazgo o requisito | Decisión en la interfaz | Por qué |
|---|---|---|
| Aspecto visual: 11/13. | Inicio destaca la **chapa QR** con ilustración propia y contraste azul/verde. | Da identidad sin saturar las pantallas de gestión. |
| Facilidad: 10/13. | Barra inferior con **icono y texto**; selectores de especie, microchip y cuidado. | Reduce memoria y escritura. |
| Rapidez: 7/13. | Uso **sin registro inicial**, plantillas y fechas rápidas. | Acorta tareas; falta validarlo con pruebas de uso. |
| Simplicidad y funciones: 4/13 cada una. | Inicio resume; historial, edición y copias se abren por sección. | Mantiene funciones sin exhibirlas todas a la vez. |
| **Requisito del proyecto**, no de la encuesta: identificar una mascota perdida. | **Chapa** central y acceso desde perfiles. | Visibiliza el QR; hoy es solo una prueba local, sin ficha pública. |

## d) Estructura y navegación

El orden **Inicio → Mascotas → Chapa → Rutina → Salud** sigue la tarea real: orientarse, registrar al animal, acceder a su identificación, planificar cuidados y consultar antecedentes. Inicio muestra pendientes; Mascotas crea el perfil del que dependen QR y registros. **Chapa es una acción central**, no una pantalla: abre el QR de la mascota seleccionada. La barra persistente evita volver al inicio. La encuesta no comparó órdenes de navegación; esta estructura responde a dependencias funcionales.

## e) Diversidad y accesibilidad

La variedad de edades y la respuesta de uso móvil poco frecuente justifican **lenguaje directo**, iconos acompañados de texto, opciones predefinidas y ayuda en estados vacíos. Los estados usan palabras, no solo color; se puede empezar sin cuenta. **Pendiente de validar:** tamaño de letra aumentado, contraste, lector de pantalla y pruebas con dueños de mascotas de diferentes edades y familiaridad tecnológica. La encuesta no sustituye esas pruebas.

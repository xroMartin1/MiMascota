# Dirección visual y chapa de Mi Mascota

La idea visual es una **identidad de regreso**: una chapa, un camino de vuelta y una señal que se reconoce al instante. La pantalla principal da protagonismo al QR sobre un bloque azul profundo (`#103D49`), con una chapa que se mueve suavemente y una acción verde suave (`#DAEFA0`). El blanco con un matiz gris (`#F7F8FA`) deja respirar el resto de la interfaz; el azul océano (`#286F83`) organiza las acciones secundarias. El resumen diario queda abierto sobre el fondo, para romper la repetición de tarjetas. Los primeros bloques de cada pantalla aparecen con una cadencia breve. La ilustración `assets/MascotsBanner.png` aporta expresividad a Rutina sin hacer infantil al resto de la app.

La referencia es la dirección de [Codegrid](https://www.youtube.com/@codegrid): contraste, composición editorial y movimiento que guía la mirada. [Codrops documenta](https://tympanus.net/codrops/2025/03/05/case-study-stefan-vitasovic-portfolio-2025/) cómo un diseño con mucho espacio y tipografía fuerte puede mantener su carácter en móvil con animación más contenida. En Mi Mascota esto se traduce en una chapa protagonista, numeración de secciones y entradas escalonadas; el QR y los cuidados siguen accesibles sin gestos especiales.

## Prompt para generar el icono

> Design a distinctive premium mobile app icon for “Mi Mascota”, a pet care and digital ID app. Core visual metaphor: a small pet ID tag with one corner shaped like a QR finder square, and a subtle curved return path carved in negative space. Strong asymmetric silhouette, memorable at 48 pixels, human tone rather than cartoon. Use ocean blue #286F83, fresh aqua #DAF0F1, soft green #DAEFA0 and a near-white cool gray #F7F8FA. Flat vector geometry with carefully balanced spacing, crisp edges, high contrast, minimal detail, centered within a generous safe area. No letters, no words, no paw as the main symbol, no heart, no animal face, no stock-app look, no glossy 3D, no gradients. Square 1024×1024 canvas. The QR reference is symbolic and must not pretend to be a scannable code.

Si generas varias opciones, elige la que se siga reconociendo al verla a 48×48 px. Exporta el resultado final en PNG 1024×1024 como `assets/app_icon.png`. Para que aparezca como icono real del APK, configura después `icon.filename = assets/app_icon.png` en `buildozer.spec`; el icono debe probarse en el launcher de Android.

## Imagen de la placa

Coloca tu imagen en **`assets/placa_preview.png`**. La app la mostrará automáticamente en la vista de la chapa. Tamaño recomendado: 1200×800 px o mayor, PNG, con la placa centrada sobre un fondo simple. Usa un nombre y QR ficticios en el mockup: la imagen es una vista previa comercial, no la placa personalizada que recibirá cada comprador.

## Flujo del producto

1. Invitado: registra mascotas y prueba un QR local sin datos privados. El período de 14 días comienza al abrir por primera vez la chapa de cada mascota.
2. Cuenta gratuita, cuando exista Supabase: activa una chapa pública con token aleatorio. La ficha se sirve desde web, por lo que la comprobación de vencimiento no depende del reloj del teléfono.
3. Persona que encuentra a la mascota: escanea la chapa, ve solo información elegida por el dueño y envía un mensaje por un formulario protegido. La página no revela teléfono, correo ni dirección por defecto.
4. Compra verificada: el mismo QR pasa a estado permanente y se imprime en una placa con el nombre de la mascota. El estado permanente solo puede activarlo un backend tras comprobar el pago; la app no puede autoconcedérselo.

La etapa 1 funciona hoy. Las etapas 2–4 requieren proyecto Supabase, página pública, gestión de pagos y proveedor de fabricación/envío; no están activadas ni simuladas como compras reales.

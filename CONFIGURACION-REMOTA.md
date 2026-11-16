# Consejo remoto de Inicio

La app lee `message` de la fila `home_care_tip` en `public.app_public_config` de Supabase y lo muestra en Inicio, debajo de la chapa QR. No es Firebase Remote Config: cumple el requisito de leer un valor de una fuente remota y reflejarlo en la interfaz.

## Demo sin paneles

1. Abrir la app con internet, incluso sin cuenta.
2. En Inicio, mostrar **Un consejo para su cuidado**.
3. Esperar **Actualizado en línea**: confirma que esa ejecución recibió un valor válido del servidor.
4. Cerrar la app, activar modo avión y reabrir: se conserva el texto y aparece **Último consejo guardado**.

Frase para exponer: «El consejo se consulta en Supabase, se refleja en Inicio y se guarda en JSON como respaldo. Podemos cambiarlo remotamente sin recompilar. Si no llega la respuesta, usamos el último valor válido o uno predeterminado».

**No se simula una conexión:** sin una respuesta remota válida no se muestra «Actualizado en línea». Si nunca hubo una respuesta válida, se muestra «Consejo disponible sin conexión» junto al texto predeterminado.

## Dónde está el código

- `services/remote_config.py`: consulta pública, validación, valor predeterminado y caché JSON.
- `screens/remote_config.py`: consulta en un hilo y actualización de la interfaz mediante `Clock`.
- `screens/features.py` / `screens/features.kv`: posición, texto y diseño del consejo.
- `screens/home.py`: carga al arrancar; `main.py`: nuevo intento al volver a la app, con límite de un intento por minuto.
- `remote-config.json`: se genera junto al JSON del invitado, en el almacenamiento local de datos. No se sube como respaldo de una cuenta ni contiene información personal. Incluye el origen y la fecha de consulta.

La consulta se hace en segundo plano y no bloquea la navegación. La caché se valida y se separa por URL del proyecto. Texto vacío, excesivo o con caracteres de control no reemplaza el último valor válido. Un error de guardado no impide mostrar el consejo recibido.

## Cambiar el valor (solo administración)

La tabla ya está preparada en el proyecto MiMascota. Los clientes solo pueden leer; ni invitados ni usuarios autenticados pueden insertar, actualizar o borrar. Nunca guardar secretos o datos personales en esta tabla pública.

En el SQL Editor del proyecto, un administrador puede ejecutar:

```sql
update public.app_public_config
set message = 'Revisa que los datos de contacto de su chapa estén al día.',
    updated_at = now()
where key = 'home_care_tip';
```

Después, reabrir la app o volver a ella tras al menos un minuto. No hace falta hacer este cambio durante la exposición.

Para preparar otro proyecto, usar `supabase/06_configuracion_remota.sql`. El APK anterior no incluye esta función: hay que recompilar e instalar una versión con el código actualizado. El cambio de un consejo después de esa instalación ya no requiere recompilar.

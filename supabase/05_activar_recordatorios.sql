-- Activar después de desplegar reminder-worker y pasar verify_recordatorios.sql.
-- La función lee su clave en Vault; el comando del cron no contiene credenciales.
select cron.schedule('mimascota-reminders','* * * * *','select reminder_private.tick();');

-- Comprobaciones de configuracion. Ejecutar en SQL Editor despues de los dos scripts.
-- Esto comprueba RLS y permisos, no sustituye una prueba con dos cuentas reales.
select c.relname as tabla, c.relrowsecurity as rls_activo
from pg_class c
where c.oid in ('public.petcare_state'::regclass,
                'public.pet_tags'::regclass,
                'public.pet_tag_messages'::regclass)
order by c.relname;

select
  has_table_privilege('anon', 'public.petcare_state', 'SELECT') as anon_lee_copia,
  has_table_privilege('authenticated', 'public.petcare_state', 'SELECT') as usuario_lee_copia,
  has_function_privilege('anon', 'public.save_petcare_state(bigint,jsonb)', 'EXECUTE') as anon_guarda_copia,
  has_function_privilege('authenticated', 'public.save_petcare_state(bigint,jsonb)', 'EXECUTE') as usuario_guarda_copia,
  has_table_privilege('anon', 'public.pet_tags', 'SELECT') as anon_enumera_chapas,
  has_table_privilege('authenticated', 'public.pet_tags', 'SELECT') as usuario_lee_chapas,
  has_table_privilege('authenticated', 'public.pet_tags', 'INSERT') as usuario_crea_chapas_directo,
  has_table_privilege('anon', 'public.pet_tag_messages', 'INSERT') as anon_envia_mensaje_directo,
  has_table_privilege('authenticated', 'public.pet_tag_messages', 'SELECT') as usuario_lee_mensajes;

select tablename, policyname, cmd, roles
from pg_policies
where schemaname = 'public'
  and tablename in ('petcare_state', 'pet_tags', 'pet_tag_messages')
order by tablename, policyname;

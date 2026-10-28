-- Ejecutar TODO el archivo en SQL Editor. Hay un solo SELECT y una sola tabla
-- de resultados: cada fila debe terminar en OK. No modifica ningun dato.
-- Comprobar tambien el acceso real con dos cuentas; SQL Editor usa privilegios elevados.
with checks (comprobacion, esperado, actual) as (
  values
    ('RLS: petcare_state', true,
      coalesce((select relrowsecurity from pg_class where oid = to_regclass('public.petcare_state')), false)),
    ('RLS: pet_tags', true,
      coalesce((select relrowsecurity from pg_class where oid = to_regclass('public.pet_tags')), false)),
    ('RLS: pet_tag_messages', true,
      coalesce((select relrowsecurity from pg_class where oid = to_regclass('public.pet_tag_messages')), false)),
    ('Anonimo NO lee copias', false,
      has_table_privilege('anon', 'public.petcare_state', 'SELECT')),
    ('Usuario lee sus copias', true,
      has_table_privilege('authenticated', 'public.petcare_state', 'SELECT')),
    ('Usuario puede crear copias', true,
      has_table_privilege('authenticated', 'public.petcare_state', 'INSERT')),
    ('Usuario puede actualizar copias', true,
      has_table_privilege('authenticated', 'public.petcare_state', 'UPDATE')),
    ('Anonimo NO ejecuta guardado', false,
      has_function_privilege('anon', 'public.save_petcare_state(bigint,jsonb)', 'EXECUTE')),
    ('Usuario ejecuta guardado', true,
      has_function_privilege('authenticated', 'public.save_petcare_state(bigint,jsonb)', 'EXECUTE')),
    ('Anonimo NO enumera chapas', false,
      has_table_privilege('anon', 'public.pet_tags', 'SELECT')),
    ('Usuario lee sus chapas', true,
      has_table_privilege('authenticated', 'public.pet_tags', 'SELECT')),
    ('Usuario NO crea chapas directamente', false,
      has_table_privilege('authenticated', 'public.pet_tags', 'INSERT')),
    ('Anonimo NO inserta mensajes directamente', false,
      has_table_privilege('anon', 'public.pet_tag_messages', 'INSERT')),
    ('Usuario lee sus mensajes', true,
      has_table_privilege('authenticated', 'public.pet_tag_messages', 'SELECT')),
    ('Existen las 5 politicas previstas', true,
      (select count(*) = 5 from pg_policies
       where schemaname = 'public'
         and (tablename, policyname) in (
           ('petcare_state', 'petcare_state_select'),
           ('petcare_state', 'petcare_state_insert'),
           ('petcare_state', 'petcare_state_update'),
           ('pet_tags', 'pet_tags_owner_select'),
           ('pet_tag_messages', 'pet_tag_messages_owner_select')
         )))
)
select comprobacion, esperado, actual,
  case when actual = esperado then 'OK' else 'REVISAR' end as resultado
from checks
order by comprobacion;

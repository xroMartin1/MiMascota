-- Mi Mascota: cuentas y copia privada.
-- Se puede volver a ejecutar sobre la version anterior sin borrar los datos.
-- Ejecutar en el SQL Editor como propietario del proyecto.
begin;

create table if not exists public.petcare_state (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null default '{}'::jsonb,
  revision bigint not null default 0,
  updated_at timestamptz not null default now(),
  constraint object_payload check (jsonb_typeof(data) = 'object')
);

alter table public.petcare_state enable row level security;
revoke all on table public.petcare_state from public, anon, authenticated;
grant select, insert, update on table public.petcare_state to authenticated;

drop policy if exists own_state on public.petcare_state;
drop policy if exists petcare_state_select on public.petcare_state;
drop policy if exists petcare_state_insert on public.petcare_state;
drop policy if exists petcare_state_update on public.petcare_state;

create policy petcare_state_select on public.petcare_state
  for select to authenticated
  using ((select auth.uid()) = owner_id);
create policy petcare_state_insert on public.petcare_state
  for insert to authenticated
  with check ((select auth.uid()) = owner_id);
create policy petcare_state_update on public.petcare_state
  for update to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create or replace function public.save_petcare_state(expected_revision bigint, payload jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare current_revision bigint;
begin
  if auth.uid() is null then raise exception 'authentication_required'; end if;
  if expected_revision is null or expected_revision < 0 then
    raise exception 'invalid_revision';
  end if;
  if jsonb_typeof(payload) <> 'object' or octet_length(payload::text) > 2000000 then
    raise exception 'invalid_payload';
  end if;

  insert into public.petcare_state(owner_id) values (auth.uid()) on conflict do nothing;
  select revision into current_revision from public.petcare_state
    where owner_id = auth.uid() for update;
  if current_revision <> expected_revision then raise exception 'revision_conflict'; end if;

  update public.petcare_state
    set data = payload, revision = revision + 1, updated_at = now()
    where owner_id = auth.uid();
  return jsonb_build_object('revision', current_revision + 1);
end;
$$;

revoke all on function public.save_petcare_state(bigint, jsonb) from public, anon, authenticated;
grant execute on function public.save_petcare_state(bigint, jsonb) to authenticated;

commit;

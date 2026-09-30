-- Ejecutar una vez en el SQL Editor del proyecto Supabase.
create table if not exists public.petcare_state (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null default '{}'::jsonb,
  revision bigint not null default 0,
  updated_at timestamptz not null default now(),
  constraint object_payload check (jsonb_typeof(data) = 'object')
);
alter table public.petcare_state enable row level security;
revoke all on public.petcare_state from anon;
grant select, insert, update on public.petcare_state to authenticated;
drop policy if exists own_state on public.petcare_state;
create policy own_state on public.petcare_state for all to authenticated
  using ((select auth.uid()) = owner_id)
  with check ((select auth.uid()) = owner_id);

create or replace function public.save_petcare_state(expected_revision bigint, payload jsonb)
returns jsonb language plpgsql security invoker set search_path = '' as $$
declare current_revision bigint;
begin
  if auth.uid() is null then raise exception 'authentication_required'; end if;
  if jsonb_typeof(payload) <> 'object' or octet_length(payload::text) > 2000000 then
    raise exception 'invalid_payload';
  end if;
  insert into public.petcare_state(owner_id) values (auth.uid()) on conflict do nothing;
  select revision into current_revision from public.petcare_state
    where owner_id = auth.uid() for update;
  if current_revision <> expected_revision then raise exception 'revision_conflict'; end if;
  update public.petcare_state set data = payload, revision = revision + 1, updated_at = now()
    where owner_id = auth.uid();
  return jsonb_build_object('revision', current_revision + 1);
end;
$$;
revoke all on function public.save_petcare_state(bigint, jsonb) from public, anon;
grant execute on function public.save_petcare_state(bigint, jsonb) to authenticated;

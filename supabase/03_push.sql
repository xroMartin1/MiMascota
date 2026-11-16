-- Backend privado de dispositivos; solo la Edge Function puede escribir o leer tokens.
create table public.push_devices (
  owner_id uuid not null references auth.users(id) on delete cascade,
  device_id uuid not null,
  token text not null check (length(token) between 32 and 4096),
  updated_at timestamptz not null default now(),
  primary key (owner_id, device_id)
);
create table public.push_test_limits (
  owner_id uuid primary key references auth.users(id) on delete cascade,
  sent_at timestamptz not null default '-infinity'
);
alter table public.push_devices enable row level security;
alter table public.push_test_limits enable row level security;
create policy push_devices_no_client_access on public.push_devices
  for all to anon, authenticated using (false) with check (false);
create policy push_limits_no_client_access on public.push_test_limits
  for all to anon, authenticated using (false) with check (false);
revoke all on public.push_devices, public.push_test_limits from public, anon, authenticated;
grant select, insert, update, delete on public.push_devices, public.push_test_limits to service_role;

create function public.claim_push_test(p_owner uuid, p_device uuid) returns text
language plpgsql security invoker set search_path = '' as $$
declare result text; claimed uuid;
begin
  select token into result from public.push_devices
    where owner_id = p_owner and device_id = p_device
      and updated_at > now() - interval '30 days' for update;
  if result is null then return null; end if;
  insert into public.push_test_limits(owner_id) values(p_owner) on conflict do nothing;
  update public.push_test_limits set sent_at = now()
    where owner_id = p_owner and sent_at < now() - interval '60 seconds'
    returning owner_id into claimed;
  if claimed is null then raise exception 'test_rate_limited'; end if;
  return result;
end; $$;
revoke all on function public.claim_push_test(uuid, uuid) from public, anon, authenticated;
grant execute on function public.claim_push_test(uuid, uuid) to service_role;

create function public.register_push_device(p_owner uuid, p_device uuid, p_token text) returns boolean
language plpgsql security invoker set search_path = '' as $$
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_owner::text, 0));
  delete from public.push_devices where owner_id = p_owner and updated_at < now() - interval '30 days';
  if not exists(select 1 from public.push_devices where owner_id = p_owner and device_id = p_device)
     and (select count(*) from public.push_devices where owner_id = p_owner) >= 5 then
    raise exception 'device_limit';
  end if;
  insert into public.push_devices(owner_id,device_id,token) values(p_owner,p_device,p_token)
    on conflict(owner_id,device_id) do update set token = excluded.token, updated_at = now();
  return true;
end; $$;
revoke all on function public.register_push_device(uuid, uuid, text) from public, anon, authenticated;
grant execute on function public.register_push_device(uuid, uuid, text) to service_role;

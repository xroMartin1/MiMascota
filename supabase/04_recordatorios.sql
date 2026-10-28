-- Calendario privado separado de la copia de seguridad. No guarda nombres ni datos médicos.
create schema if not exists reminder_private;
revoke all on schema reminder_private from public, anon, authenticated;
create extension if not exists pg_cron;
create extension if not exists pg_net with schema extensions;

create table public.reminder_plans (
 owner_id uuid primary key references auth.users(id) on delete cascade,
 payload jsonb not null default '{"enabled":false,"timezone":"UTC","routines":[]}',
 revision bigint not null default 0,
 updated_at timestamptz not null default now()
);
create table public.reminder_schedule (
 owner_id uuid not null references auth.users(id) on delete cascade,
 task_id text not null,
 signature text not null,
 local_due timestamp not null,
 zone text not null,
 step_days integer not null check(step_days in (0,1,7)),
 next_local timestamp,
 primary key(owner_id,task_id)
);
create table public.reminder_deliveries (
 id uuid primary key default gen_random_uuid(),
 owner_id uuid not null references auth.users(id) on delete cascade,
 task_id text not null,
 device_id uuid not null,
 signature text not null,
 occurrence timestamptz not null,
 status text not null default 'pending' check(status in ('pending','sending','sent','cancelled','expired','failed','uncertain')),
 attempts integer not null default 0,
 retry_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(owner_id,task_id,occurrence,device_id),
 foreign key(owner_id,device_id) references public.push_devices(owner_id,device_id) on delete cascade
);
create index reminder_next_idx on public.reminder_schedule(next_local) where next_local is not null;
create index reminder_pending_idx on public.reminder_deliveries(retry_at) where status='pending';
create index reminder_owner_idx on public.reminder_deliveries(owner_id,task_id);
alter table public.reminder_plans enable row level security;
alter table public.reminder_schedule enable row level security;
alter table public.reminder_deliveries enable row level security;
create policy reminders_no_client on public.reminder_plans for all to anon,authenticated using(false) with check(false);
create policy schedules_no_client on public.reminder_schedule for all to anon,authenticated using(false) with check(false);
create policy deliveries_no_client on public.reminder_deliveries for all to anon,authenticated using(false) with check(false);
revoke all on public.reminder_plans, public.reminder_schedule, public.reminder_deliveries from public,anon,authenticated;
grant select,insert,update,delete on public.reminder_plans, public.reminder_schedule, public.reminder_deliveries to service_role;

-- Solo el endpoint autenticado obtiene p_owner desde Supabase Auth.
create function public.save_reminder_plan(p_owner uuid,p_revision bigint,p_payload jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare old_plan public.reminder_plans%rowtype; item jsonb; zone_name text; ids text[] := '{}';
 due timestamp; sig text; days integer; task text;
begin
 if p_revision is null or p_revision<0 or jsonb_typeof(p_payload) is distinct from 'object'
    or octet_length(p_payload::text)>200000 or jsonb_typeof(p_payload->'enabled') is distinct from 'boolean'
    or jsonb_typeof(p_payload->'routines') is distinct from 'array' then raise exception 'invalid_plan'; end if;
 zone_name:=p_payload->>'timezone';
 if zone_name is null or not exists(select 1 from pg_catalog.pg_timezone_names where name=zone_name)
    or jsonb_array_length(p_payload->'routines')>500 then raise exception 'invalid_plan'; end if;
 insert into public.reminder_plans(owner_id) values(p_owner) on conflict do nothing;
 select * into old_plan from public.reminder_plans where owner_id=p_owner for update;
 -- Recupera una respuesta perdida sin crear otra revisión ni reprogramar avisos.
 if old_plan.payload=p_payload then return jsonb_build_object('revision',old_plan.revision); end if;
 if old_plan.revision<>p_revision then raise exception 'plan_conflict'; end if;
 if (p_payload->>'enabled')::boolean then
  for item in select value from jsonb_array_elements(p_payload->'routines') loop
   task:=item->>'id';
   if task is null or task !~ '^[a-zA-Z0-9_-]{1,64}$' or task=any(ids)
      or jsonb_typeof(item->'done') is distinct from 'boolean'
      or coalesce(item->>'repeat','') not in ('No','Diaria','Semanal') then raise exception 'invalid_plan'; end if;
   ids:=array_append(ids,task);
   if (item->>'done')::boolean or coalesce(item->>'due_at','')='' then
    delete from public.reminder_schedule where owner_id=p_owner and task_id=task;
    continue;
   end if;
   if item->>'due_at' !~ '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$' then raise exception 'invalid_plan'; end if;
   due:=(item->>'due_at')::timestamp;
   if extract(year from due) not between 2000 and 2100 then raise exception 'invalid_plan'; end if;
   days:=case item->>'repeat' when 'Diaria' then 1 when 'Semanal' then 7 else 0 end;
   sig:=md5(task || '|' || due::text || '|' || zone_name || '|' || days::text);
   insert into public.reminder_schedule(owner_id,task_id,signature,local_due,zone,step_days,next_local)
    values(p_owner,task,sig,due,zone_name,days,due)
    on conflict(owner_id,task_id) do update set signature=excluded.signature,local_due=excluded.local_due,
      zone=excluded.zone,step_days=excluded.step_days,
      next_local=case when reminder_schedule.signature=excluded.signature then reminder_schedule.next_local else excluded.next_local end;
  end loop;
  delete from public.reminder_schedule where owner_id=p_owner and not(task_id=any(ids));
 else
  delete from public.reminder_schedule where owner_id=p_owner;
 end if;
 update public.reminder_deliveries d set status='cancelled',updated_at=now()
  where d.owner_id=p_owner and d.status in ('pending','sending') and not exists(
    select 1 from public.reminder_schedule s where s.owner_id=d.owner_id and s.task_id=d.task_id and s.signature=d.signature);
 update public.reminder_plans set payload=p_payload,revision=revision+1,updated_at=now() where owner_id=p_owner
  returning * into old_plan;
 return jsonb_build_object('revision',old_plan.revision);
end; $$;
revoke all on function public.save_reminder_plan(uuid,bigint,jsonb) from public,anon,authenticated;
grant execute on function public.save_reminder_plan(uuid,bigint,jsonb) to service_role;

-- Generado y conservado en Vault: no se imprime ni se incluye en el APK.
do $$ begin
 if not exists(select 1 from vault.secrets where name='reminder_worker_key') then
  perform vault.create_secret(encode(extensions.gen_random_bytes(32),'hex'),'reminder_worker_key');
 end if;
end; $$;
create function reminder_private.authorized(p_key text) returns boolean
language sql security definer set search_path='' as $$
 select length(p_key)=64 and exists(select 1 from vault.decrypted_secrets
  where name='reminder_worker_key' and decrypted_secret=p_key);
$$;
revoke all on function reminder_private.authorized(text) from public,anon,authenticated;
grant usage on schema reminder_private to service_role;
grant execute on function reminder_private.authorized(text) to service_role;

create function public.claim_reminder_jobs(p_key text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare s public.reminder_schedule%rowtype; local_now timestamp; occurrence_time timestamptz; output jsonb;
begin
 if not coalesce(reminder_private.authorized(p_key),false) then raise exception 'worker_unauthorized'; end if;
 -- Un envío cuya respuesta se perdió no se repite: entrega incierta, no entrega confirmada.
 update public.reminder_deliveries set status='uncertain',updated_at=now()
  where status='sending' and updated_at<now()-interval '5 minutes';
 update public.reminder_deliveries set status='expired',updated_at=now()
  where status='pending' and occurrence<now()-interval '15 minutes';
 for s in select * from public.reminder_schedule where next_local is not null
    and (next_local at time zone zone)<=now() order by next_local limit 500 for update skip locked loop
  local_now:=now() at time zone s.zone;
  -- Salta ocurrencias antiguas; no envía una ráfaga de medicaciones atrasadas.
  if s.step_days>0 and (s.next_local at time zone s.zone)<now()-interval '15 minutes' then
   s.next_local:=s.next_local + make_interval(days=>s.step_days * greatest(0,
      floor(extract(epoch from (local_now-s.next_local))/(86400*s.step_days))::integer));
  end if;
  occurrence_time:=s.next_local at time zone s.zone;
  if occurrence_time between now()-interval '15 minutes' and now() then
   insert into public.reminder_deliveries(owner_id,task_id,device_id,signature,occurrence)
    select s.owner_id,s.task_id,d.device_id,s.signature,occurrence_time from public.push_devices d
     where d.owner_id=s.owner_id and d.updated_at>now()-interval '30 days' on conflict do nothing;
  end if;
  update public.reminder_schedule set next_local=case when s.step_days=0 then null
     when occurrence_time<=now() then s.next_local+make_interval(days=>s.step_days) else s.next_local end
    where owner_id=s.owner_id and task_id=s.task_id;
 end loop;
 with selected as (
  select id from public.reminder_deliveries where status='pending' and retry_at<=now()
   order by retry_at limit 20 for update skip locked
 ), claimed as (
  update public.reminder_deliveries d set status='sending',attempts=attempts+1,updated_at=now()
   from selected c where d.id=c.id returning d.*
 ) select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'token',p.token)), '[]'::jsonb) into output
 from claimed c join public.push_devices p on p.owner_id=c.owner_id and p.device_id=c.device_id;
 -- Limita conservación del historial técnico, sin cuerpos de mensajes ni tokens.
 delete from public.reminder_deliveries where updated_at<now()-interval '30 days';
 return output;
end; $$;
revoke all on function public.claim_reminder_jobs(text) from public,anon,authenticated;
grant execute on function public.claim_reminder_jobs(text) to service_role;

create function public.prepare_reminder_job(p_key text,p_id uuid,p_token text) returns boolean
language plpgsql security invoker set search_path='' as $$
begin
 if not coalesce(reminder_private.authorized(p_key),false) then raise exception 'worker_unauthorized'; end if;
 return exists(select 1 from public.reminder_deliveries d
   join public.push_devices p on p.owner_id=d.owner_id and p.device_id=d.device_id
   join public.reminder_schedule s on s.owner_id=d.owner_id and s.task_id=d.task_id and s.signature=d.signature
   where d.id=p_id and d.status='sending' and p.token=p_token and p.updated_at>now()-interval '30 days');
end; $$;
create function public.finish_reminder_job(p_key text,p_id uuid,p_result text,p_token text default null) returns void
language plpgsql security invoker set search_path='' as $$
declare d public.reminder_deliveries%rowtype;
begin
 if not coalesce(reminder_private.authorized(p_key),false) then raise exception 'worker_unauthorized'; end if;
 if p_result not in ('sent','retry','failed','uncertain','cancelled','unregistered') then raise exception 'invalid_result'; end if;
 select * into d from public.reminder_deliveries where id=p_id for update;
 if not found or d.status<>'sending' then return; end if;
 if p_result='unregistered' then
  delete from public.push_devices where owner_id=d.owner_id and device_id=d.device_id and token=p_token;
  return;
 end if;
 update public.reminder_deliveries set status=case when p_result='retry' and attempts<3 then 'pending'
     when p_result='retry' then 'failed' else p_result end,
   retry_at=now()+make_interval(secs=>60*attempts),updated_at=now() where id=p_id;
end; $$;
revoke all on function public.prepare_reminder_job(text,uuid,text),public.finish_reminder_job(text,uuid,text,text) from public,anon,authenticated;
grant execute on function public.prepare_reminder_job(text,uuid,text),public.finish_reminder_job(text,uuid,text,text) to service_role;

create function reminder_private.tick() returns bigint
language plpgsql security definer set search_path='' as $$
declare worker_key text;
begin
 -- Si no hay planes ni entregas pendientes, no consume invocaciones Edge.
 if not exists(select 1 from public.reminder_schedule where next_local is not null and (next_local at time zone zone)<=now())
    and not exists(select 1 from public.reminder_deliveries where status='pending' and retry_at<=now())
    and not exists(select 1 from public.reminder_deliveries where status='sending' and updated_at<now()-interval '5 minutes') then return null; end if;
 select decrypted_secret into worker_key from vault.decrypted_secrets where name='reminder_worker_key';
 return net.http_post(url:='https://thkzrjwalcxfiucqppfv.supabase.co/functions/v1/reminder-worker',
   headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||worker_key),
   body:='{}'::jsonb,timeout_milliseconds:=120000);
end; $$;
revoke all on function reminder_private.tick() from public,anon,authenticated,service_role;
-- Se activa al terminar las verificaciones (05_activar_recordatorios.sql).

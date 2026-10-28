-- Fixtures privados transaccionales: nunca disparan HTTP/FCM y se revierten al terminar.
begin;
do $$
declare owner uuid; device uuid := '90000000-0000-4000-8000-000000000001'; key text;
 payload jsonb; result jsonb; jobs jsonb; job uuid; weekly_job uuid; revision bigint;
begin
 select id into owner from auth.users limit 1;
 if owner is null then raise exception 'test_needs_account'; end if;
 select decrypted_secret into key from vault.decrypted_secrets where name='reminder_worker_key';
 insert into public.push_devices(owner_id,device_id,token) values(owner,device,repeat('fixture',10));
 payload:=jsonb_build_object('enabled',true,'timezone','UTC','routines',jsonb_build_array(
   jsonb_build_object('id','fixture_once','due_at',to_char(now() at time zone 'UTC','YYYY-MM-DD HH24:MI'),'done',false,'repeat','No'),
   jsonb_build_object('id','fixture_weekly','due_at',to_char((now() at time zone 'UTC')-interval '28 days','YYYY-MM-DD HH24:MI'),'done',false,'repeat','Semanal'),
   jsonb_build_object('id','fixture_old','due_at',to_char((now() at time zone 'UTC')-interval '30 minutes','YYYY-MM-DD HH24:MI'),'done',false,'repeat','No')));
 result:=public.save_reminder_plan(owner,0,payload);
 assert (result->>'revision')::bigint=1,'first revision';
 assert public.save_reminder_plan(owner,0,payload)=result,'lost-response idempotency';
 begin
  perform public.save_reminder_plan(owner,0,jsonb_set(payload,'{enabled}','false'));
  raise exception 'conflict_missing';
 exception when others then if sqlerrm<>'plan_conflict' then raise; end if; end;
 begin
  perform public.claim_reminder_jobs(repeat('0',64)); raise exception 'worker_auth_missing';
 exception when others then if sqlerrm<>'worker_unauthorized' then raise; end if; end;
 jobs:=public.claim_reminder_jobs(key);
 -- Se cuenta solo el fixture, aunque haya teléfonos reales registrados del propietario.
 assert (select count(*) from public.reminder_deliveries where device_id=device and status='sending')=2,'once and weekly, no stale alert';
 assert jsonb_array_length(public.claim_reminder_jobs(key))=0,'second worker cannot double claim';
 select id into job from public.reminder_deliveries where device_id=device and task_id='fixture_once';
 select id into weekly_job from public.reminder_deliveries where device_id=device and task_id='fixture_weekly';
 assert public.prepare_reminder_job(key,job,repeat('fixture',10)),'live job';
 payload:=jsonb_set(payload,'{routines,0,done}','true');
 perform public.save_reminder_plan(owner,1,payload);
 assert not public.prepare_reminder_job(key,job,repeat('fixture',10)),'completed care cancels claimed job';
 perform public.finish_reminder_job(key,weekly_job,'retry');
 update public.reminder_deliveries set retry_at=now() where id=weekly_job;
 perform public.claim_reminder_jobs(key);
 assert (select attempts from public.reminder_deliveries where id=weekly_job)=2,'bounded retry';
 perform public.finish_reminder_job(key,weekly_job,'uncertain');
 assert jsonb_array_length(public.claim_reminder_jobs(key))=0,'uncertain send not retried';
 assert (select next_local>now() at time zone 'UTC' from public.reminder_schedule where owner_id=owner and task_id='fixture_weekly'),'weekly advanced';
 perform public.save_reminder_plan(owner,2,jsonb_set(payload,'{enabled}','false'));
 assert not exists(select 1 from public.reminder_schedule where owner_id=owner),'disable removes calendar';
 begin
  perform public.save_reminder_plan(owner,3,jsonb_set(payload,'{timezone}','"No/SuchZone"'));
  raise exception 'zone_missing';
 exception when others then if sqlerrm<>'invalid_plan' then raise; end if; end;
 assert ('2026-09-05 09:00'::timestamp at time zone 'America/Santiago')=
        '2026-09-05 13:00+00'::timestamptz,'before DST';
 assert ('2026-09-07 09:00'::timestamp at time zone 'America/Santiago')=
        '2026-09-07 12:00+00'::timestamptz,'after DST, same local hour';
end; $$;
rollback;

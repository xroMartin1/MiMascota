begin;
create temporary table scan_fixture as select gen_random_uuid() as owner, gen_random_uuid() as tag, gen_random_uuid() as code;
insert into auth.users(id) select owner from scan_fixture;
insert into public.petcare_state(owner_id,data)
select owner,'{"pets":[{"id":"scan-fixture","name":"Mascota de prueba","kind":"Perro"}]}'::jsonb from scan_fixture;
insert into public.pet_tags(id,owner_id,pet_id,scan_code,public_name,species,expires_at)
select tag,owner,'scan-fixture',code,'Mascota de prueba','Perro',now()+interval '1 day' from scan_fixture;
grant select on scan_fixture to service_role;
set local role service_role;
do $$
declare code uuid; tag uuid;
begin
  select s.code,s.tag into code,tag from scan_fixture s;
  if not public.queue_qr_scan_notice(code) then raise exception 'first scan did not queue'; end if;
  if public.queue_qr_scan_notice(code) then raise exception 'duplicate scan was not throttled'; end if;
  if (select count(*) from qr_private.contact_push_outbox where tag_id=tag and event_kind='scan')<>1 then
    raise exception 'wrong number of scan notices'; end if;
  update public.pet_tags set scan_notified_at=now()-interval '11 minutes',status='disabled' where id=tag;
  if public.queue_qr_scan_notice(code) then raise exception 'disabled tag queued'; end if;
  update public.pet_tags set status='active',created_at=now()-interval '2 days',expires_at=now()-interval '1 day' where id=tag;
  if public.queue_qr_scan_notice(code) then raise exception 'expired tag queued'; end if;
end $$;
reset role;
select
 not has_function_privilege('anon','public.queue_qr_scan_notice(uuid)','execute') as anonymous_denied,
 not has_function_privilege('authenticated','public.queue_qr_scan_notice(uuid)','execute') as user_denied,
 'PASS: first scan, cooldown, disabled and expired tags' as checks;
rollback;

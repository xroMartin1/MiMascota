alter table qr_private.contact_push_outbox
  alter column message_id drop not null,
  alter column thread_id drop not null,
  add column event_kind text not null default 'message' check(event_kind in ('message','scan')),
  add column tag_id uuid references public.pet_tags(id) on delete cascade,
  add constraint push_event_payload check (
    (event_kind='message' and message_id is not null and thread_id is not null)
    or (event_kind='scan' and tag_id is not null and message_id is null and thread_id is null));
alter table public.pet_tags add column scan_notified_at timestamptz;

create function public.queue_qr_scan_notice(p_scan_code uuid) returns boolean
language plpgsql security invoker set search_path='' as $$
declare tag public.pet_tags;
begin
  if current_user<>'service_role' then raise exception 'server_only'; end if;
  select * into tag from public.pet_tags where scan_code=p_scan_code for update;
  if tag.id is null or tag.status<>'active' or tag.expires_at<=clock_timestamp()
    or public.lookup_public_tag(p_scan_code)->>'status'<>'active' then return false; end if;
  if tag.scan_notified_at>clock_timestamp()-interval '10 minutes' then return false; end if;
  insert into qr_private.contact_push_outbox(owner_id,event_kind,tag_id)
    values(tag.owner_id,'scan',tag.id);
  update public.pet_tags set scan_notified_at=clock_timestamp() where id=tag.id;
  return true;
end $$;
revoke all on function public.queue_qr_scan_notice(uuid) from public,anon,authenticated;
grant execute on function public.queue_qr_scan_notice(uuid) to service_role;

create or replace function public.claim_qr_contact_push() returns jsonb
language plpgsql security invoker set search_path='' as $$
declare job qr_private.contact_push_outbox; tokens jsonb; lease_key uuid;
begin
  if current_user<>'service_role' then raise exception 'server_only'; end if;
  delete from qr_private.contact_threads where expires_at<=clock_timestamp();
  delete from qr_private.contact_write_budget where bucket<clock_timestamp()-interval '1 day';
  delete from qr_private.contact_push_outbox where event_kind='scan' and created_at<clock_timestamp()-interval '1 day';
  select * into job from qr_private.contact_push_outbox
    where (state='pending' and available_at<=clock_timestamp()) or (state='sending' and lease_until<clock_timestamp())
    order by available_at for update skip locked limit 1;
  if job.id is null then return null; end if;
  if job.attempts>=5 then
    update qr_private.contact_push_outbox set state='failed',last_error=coalesce(last_error,'firebase_send') where id=job.id;
    return jsonb_build_object('skip',true);
  end if;
  if (job.event_kind='message' and (
      not exists(select 1 from qr_private.contact_threads where id=job.thread_id and status in ('open','contacted'))
      or exists(select 1 from qr_private.contact_threads t join qr_private.contact_messages m on m.id=job.message_id
        where t.id=job.thread_id and t.owner_read_at>=m.created_at)))
    or (job.event_kind='scan' and not exists(select 1 from public.pet_tags where id=job.tag_id
        and owner_id=job.owner_id and status='active' and expires_at>clock_timestamp())) then
    update qr_private.contact_push_outbox set state='sent',last_error='closed' where id=job.id;
    return jsonb_build_object('skip',true);
  end if;
  select coalesce(jsonb_agg(jsonb_build_object('device_id',device_id,'token',token)),'[]'::jsonb) into tokens
    from public.push_devices where owner_id=job.owner_id and updated_at>clock_timestamp()-interval '30 days';
  lease_key:=gen_random_uuid();
  update qr_private.contact_push_outbox set state='sending',attempts=attempts+1,lease=lease_key,
    lease_until=clock_timestamp()+interval '2 minutes' where id=job.id;
  return jsonb_build_object('id',job.id,'lease',lease_key,'owner_id',job.owner_id,
    'event',job.event_kind,'thread_id',job.thread_id,'devices',tokens);
end $$;

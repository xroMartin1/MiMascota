-- Public copy only. Run once on a new project; already applied to MiMascota.
create table public.app_public_config (
  key text primary key check (key = 'home_care_tip'),
  message text not null check (char_length(btrim(message)) between 1 and 200),
  updated_at timestamptz not null default now()
);
alter table public.app_public_config enable row level security;
revoke all on public.app_public_config from public, anon, authenticated;
grant select on public.app_public_config to anon, authenticated;
create policy public_care_tip_read on public.app_public_config
  for select to anon, authenticated using (key = 'home_care_tip');
comment on table public.app_public_config is
  'Public app copy only. Never store contacts, tokens or private settings here. Clients have read-only access.';
insert into public.app_public_config(key, message) values
  ('home_care_tip', 'Mantén actualizados los datos de contacto de su chapa QR. Si alguien encuentra a tu mascota, podrá avisarte.');
notify pgrst, 'reload schema';

-- Verification: rls_activo, invitado_lee, usuario_lee must be true;
-- invitado_escribe and usuario_escribe must be false.
select
  (select relrowsecurity from pg_class where oid = 'public.app_public_config'::regclass) as rls_activo,
  has_table_privilege('anon','public.app_public_config','select') as invitado_lee,
  has_table_privilege('anon','public.app_public_config','insert,update,delete,truncate') as invitado_escribe,
  has_table_privilege('authenticated','public.app_public_config','select') as usuario_lee,
  has_table_privilege('authenticated','public.app_public_config','insert,update,delete,truncate') as usuario_escribe;

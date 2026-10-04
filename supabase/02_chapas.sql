-- Mi Mascota: base privada para chapas QR y mensajes de hallazgo.
-- Ejecutar DESPUES de schema.sql. Es aditivo y no borra petcare_state.
-- Este SQL no publica una pagina web ni habilita el escaneo por si solo.
begin;

create table if not exists public.pet_tags (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  pet_id text not null,
  scan_code uuid not null unique default gen_random_uuid(),
  public_name text not null,
  species text not null,
  tag_kind text not null default 'trial',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint pet_tags_owner_pet_kind_unique unique (owner_id, pet_id, tag_kind),
  constraint pet_tags_id_owner_unique unique (id, owner_id),
  constraint pet_tags_pet_id_length check (char_length(btrim(pet_id)) between 1 and 64),
  constraint pet_tags_name_length check (char_length(btrim(public_name)) between 1 and 48),
  constraint pet_tags_species_length check (char_length(btrim(species)) between 1 and 32),
  constraint pet_tags_status_check check (status in ('active', 'disabled')),
  constraint pet_tags_kind_check check (tag_kind in ('trial', 'physical')),
  constraint pet_tags_period_check check (
    (tag_kind = 'trial' and expires_at is not null
      and expires_at > created_at
      and expires_at <= created_at + interval '14 days')
    or (tag_kind = 'physical' and expires_at is null)
  )
);

create index if not exists pet_tags_owner_idx on public.pet_tags (owner_id);
alter table public.pet_tags enable row level security;
revoke all on table public.pet_tags from public, anon, authenticated;
grant select on table public.pet_tags to authenticated;
grant select, insert, update on table public.pet_tags to service_role;

drop policy if exists pet_tags_owner_select on public.pet_tags;
create policy pet_tags_owner_select on public.pet_tags
  for select to authenticated
  using ((select auth.uid()) = owner_id);

create table if not exists public.pet_tag_messages (
  id uuid primary key default gen_random_uuid(),
  tag_id uuid not null,
  owner_id uuid not null,
  finder_name text not null,
  finder_contact text not null,
  message text not null,
  created_at timestamptz not null default now(),
  constraint pet_tag_messages_tag_owner_fkey foreign key (tag_id, owner_id)
    references public.pet_tags(id, owner_id) on delete cascade,
  constraint pet_tag_messages_name_length check (char_length(btrim(finder_name)) between 1 and 80),
  constraint pet_tag_messages_contact_length check (char_length(btrim(finder_contact)) between 3 and 180),
  constraint pet_tag_messages_body_length check (char_length(btrim(message)) between 1 and 1000)
);

create index if not exists pet_tag_messages_owner_created_idx
  on public.pet_tag_messages (owner_id, created_at desc);
alter table public.pet_tag_messages enable row level security;
revoke all on table public.pet_tag_messages from public, anon, authenticated;
grant select on table public.pet_tag_messages to authenticated;
grant select, insert on table public.pet_tag_messages to service_role;

drop policy if exists pet_tag_messages_owner_select on public.pet_tag_messages;
create policy pet_tag_messages_owner_select on public.pet_tag_messages
  for select to authenticated
  using ((select auth.uid()) = owner_id);

commit;

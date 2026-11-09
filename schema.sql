-- Moving sale database. Run once: psql "$DATABASE_URL" -f schema.sql
-- Visitors (anon) read everything except Inactive items. Only admins write.
-- Admin = a user whose app_metadata has "role": "admin" (users can't change app_metadata themselves):
--   update auth.users set raw_app_meta_data = raw_app_meta_data || '{"role":"admin"}' where email = '...';

create table public.items (
  id uuid primary key default gen_random_uuid(),
  item text not null check (length(trim(item)) > 0),   -- English name
  item_he text,                                         -- Hebrew; blank = show English
  category text,
  category_he text,
  description text,                                     -- may end with a product URL, shown as "More info"
  description_he text,
  status text not null default 'For Sale'
    check (status in ('For Sale', 'Free', 'Available Soon', 'Reserved', 'Sold', 'Given Away', 'Inactive')),
  available_from date,                                  -- for "Available Soon"
  price integer check (price >= 0),                     -- whole shekels; null = free / ask
  room text,
  -- Photo storage paths (bucket item-photos) or full https URLs; the first is the cover.
  photos text[] not null default '{}',
  created_at timestamptz not null default now()
);

comment on table public.items is
  'Moving sale items shown on omrisch.github.io/moving-sale. Inactive = hidden from visitors. '
  'Sold/Given Away stay visible, grayed out. Fill the *_he columns with Hebrew translations.';

alter table public.items enable row level security;

grant select on public.items to anon, authenticated;
grant insert, update, delete on public.items to authenticated;

create policy "Visitors see active items" on public.items for select to anon
  using (status <> 'Inactive');

create policy "Admins do everything" on public.items for all to authenticated
  using ((select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
  with check ((select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- Public bucket: a photo is viewable by its URL, but visitors can't list the bucket.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('item-photos', 'item-photos', true, 5242880, array['image/webp', 'image/jpeg']);

create policy "Admins manage item photos" on storage.objects for all to authenticated
  using (bucket_id = 'item-photos' and (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
  with check (bucket_id = 'item-photos' and (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- ---------- Pickups / deliveries (added 2026-11-09) ----------
-- Admin-only: holds buyers' names and phones, so visitors can't read it at all.
-- Written mostly by an assistant from WhatsApp chats, sometimes by hand on pickups.html.
create table public.pickups (
  id uuid primary key default gen_random_uuid(),
  day date not null,                                    -- local Israel date
  at time,                                              -- local Israel time; null = "sometime that day"
  kind text not null default 'Pickup' check (kind in ('Pickup', 'Delivery')),
  place text,                                           -- 'Home', 'Office', or a delivery address
  contact_name text,
  contact_phone text,                                   -- e.g. 0541234567 or +972541234567
  item_ids uuid[] not null default '{}',                -- items.id of what they're taking
  notes text,                                           -- anything else, incl. items not listed on the site
  done boolean not null default false,
  created_at timestamptz not null default now()
);

comment on table public.pickups is
  'Moving-sale pickup/delivery calendar shown on pickups.html (admins only). One row per appointment. '
  'day/at are local Israel date/time, no timezone. place: Home (Ramat Gan) or Office (Tel Aviv, small items) '
  'or a delivery address. item_ids = ids from public.items; when a pickup is agreed, also set those items to Reserved.';

alter table public.pickups enable row level security;
grant select, insert, update, delete on public.pickups to authenticated;
create policy "Admins do everything" on public.pickups for all to authenticated
  using ((select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin')
  with check ((select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin');

-- Items on a pickup/delivery become Reserved automatically, whoever writes the row (page, WhatsApp
-- assistant, SQL). Only items still available; Sold / Given Away / Inactive are left alone.
create function public.reserve_pickup_items() returns trigger language plpgsql as $$
begin
  update public.items set status = 'Reserved'
  where id = any(new.item_ids) and status in ('For Sale', 'Free', 'Available Soon');
  return new;
end $$;

create trigger reserve_pickup_items after insert or update of item_ids on public.pickups
  for each row execute function public.reserve_pickup_items();

comment on table public.pickups is
  'Moving-sale pickup/delivery calendar shown on pickups.html (admins only). One row per appointment. '
  'day/at are local Israel date/time, no timezone. place: Home (Ramat Gan) or Office (Tel Aviv, small items) '
  'or a delivery address. item_ids = ids from public.items; those items are set to Reserved automatically (trigger).';

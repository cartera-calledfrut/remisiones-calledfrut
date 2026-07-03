-- Ejecuta este script en el SQL Editor de Supabase (una sola vez)

create table remisiones (
  id               serial primary key,
  numero           text,
  cliente_nombre   text not null,
  cliente_nit      text not null,
  cliente_telefono text default '',
  cliente_direccion text default '',
  cliente_ciudad   text default '',
  punto_nombre     text not null,
  punto_ciudad     text not null,
  fecha            date not null,
  items            jsonb not null,
  created_at       timestamptz default now()
);

-- Nuevas tablas
create table if not exists empresas (
  id           serial primary key,
  nombre       text not null,
  nit          text not null,
  telefono     text default '',
  email        text default '',
  direccion    text default '',
  ciudad       text default '',
  logo_base64  text default ''
);

create table if not exists clientes (
  id        serial primary key,
  nombre    text not null,
  nit       text not null,
  telefono  text default '',
  direccion text default '',
  ciudad    text default '',
  activo    boolean default true
);

create table if not exists puntos_entrega (
  id         serial primary key,
  cliente_id integer references clientes(id) on delete cascade,
  nombre     text not null,
  ciudad     text default ''
);

-- Agregar empresa_id a remisiones existentes
alter table remisiones add column if not exists empresa_id integer references empresas(id);

-- Desactivar RLS y dar permisos
alter table empresas disable row level security;
alter table clientes disable row level security;
alter table puntos_entrega disable row level security;

grant select, insert, update, delete on public.empresas to anon;
grant usage, select on sequence public.empresas_id_seq to anon;
grant select, insert, update, delete on public.clientes to anon;
grant usage, select on sequence public.clientes_id_seq to anon;
grant select, insert, update, delete on public.puntos_entrega to anon;
grant usage, select on sequence public.puntos_entrega_id_seq to anon;

-- Empresa inicial
insert into empresas (nombre, nit, telefono, email, direccion, ciudad) values
('Sierra Viva SAS', '901.321.715-3', '3194839769', 'cartera@calledfrut.co', 'Cra 27 20 Sur 101', 'Medellín - Colombia');

-- Clientes
insert into clientes (nombre, nit, telefono, direccion, ciudad) values
('ESTRATEGIA VERDE S.A.S',       '901.441.798-9', '3214560847', 'Cl 57 43 47', 'Rionegro - Colombia'),
('GRUPO DANFER DE COLOMBIA SAS', '900.661.278-X', '', '', ''),
('TATORE HOLDING SAS',           '901.978.856-X', '', '', '');

-- Puntos de entrega
insert into puntos_entrega (cliente_id, nombre, ciudad) values
(1,'SIMONA - LA CEJA','La Ceja'),
(1,'SIMONA - RIONEGRO','Rionegro'),
(1,'SIMONA - CARMEN','El Carmen de Viboral'),
(1,'SIMONA - MARINILLA','Marinilla'),
(2,'MADELO-TESORO','Medellín'),
(2,'MADELO-EAFIT','Medellín'),
(2,'MADELO-VIVA','Envigado'),
(2,'MADELO-TERRACINA','Envigado'),
(2,'MADELO-FRONTERA','Envigado'),
(2,'MADELO-LAURELES','Medellín'),
(2,'MADELO-JARDINES','Rionegro'),
(2,'MADELO-TULUA','Tuluá'),
(2,'MADELO-SAN LUCAS','Medellín'),
(2,'MADELO-OVIEDO','Medellín'),
(2,'MADELO-SAN NICOLAS','Rionegro'),
(2,'MADELO-ARKADIA','Medellín'),
(2,'MADELO-CALI','Cali'),
(2,'MADELO-SANTA FE','Medellín'),
(2,'MADELO-BOGOTA','Bogotá'),
(3,'MADELO-TESORO','Medellín'),
(3,'MADELO-EAFIT','Medellín'),
(3,'MADELO-VIVA','Envigado'),
(3,'MADELO-TERRACINA','Envigado'),
(3,'MADELO-FRONTERA','Envigado'),
(3,'MADELO-LAURELES','Medellín'),
(3,'MADELO-JARDINES','Rionegro'),
(3,'MADELO-TULUA','Tuluá'),
(3,'MADELO-SAN LUCAS','Medellín'),
(3,'MADELO-OVIEDO','Medellín'),
(3,'MADELO-SAN NICOLAS','Rionegro'),
(3,'MADELO-ARKADIA','Medellín'),
(3,'MADELO-CALI','Cali'),
(3,'MADELO-SANTA FE','Medellín'),
(3,'MADELO-BOGOTA','Bogotá');

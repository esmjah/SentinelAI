-- Optional: move the historian from CSV files to Supabase Postgres (or TimescaleDB).
-- Not needed for the demo; CsvHistorian implements the same read interface.
create table if not exists measurements (
  case_id text not null,
  tag     text not null,
  t_h     double precision not null,      -- hours since case start (use timestamptz in production)
  value   double precision,               -- null where a manual reading does not exist
  quality text default 'GOOD',
  primary key (case_id, tag, t_h)
);
-- With TimescaleDB:  select create_hypertable('measurements', 't_h', chunk_time_interval => 24);
create table if not exists bleed_log (
  case_id text not null, t_h double precision not null, event text not null, annulus text not null,
  p_bar double precision, gas_sm3 double precision, liq_l double precision
);
alter table measurements enable row level security;
alter table bleed_log enable row level security;

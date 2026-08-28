-- ============================================================
-- MIGRAÇÃO 005 — Módulo de primeiro acesso.
-- ============================================================
-- NÃO DESTRUTIVA. Execute inteira no SQL Editor do Supabase,
-- depois das migrações 002, 003 e 004.
--
-- Usuários já existentes NÃO são forçados a trocar senha (default
-- false). A partir de agora, toda conta criada em Configurações →
-- Usuários nasce com deve_trocar_senha = true, e o sistema bloqueia
-- o acesso até a pessoa trocar a senha provisória pela dela.
-- ============================================================

alter table usuarios
    add column if not exists deve_trocar_senha boolean not null default false;

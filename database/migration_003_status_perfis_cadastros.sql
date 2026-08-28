-- ============================================================
-- MIGRAÇÃO 003 — Status "Aguardando substituição"/"Substituído",
-- motivos de quebra editáveis, perfil Supervisor/Monitor.
-- ============================================================
-- NÃO DESTRUTIVA. Execute inteira no SQL Editor do Supabase.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Novos status de equipamento
-- ------------------------------------------------------------
alter table equipamentos drop constraint if exists equipamentos_status_check;
alter table equipamentos add constraint equipamentos_status_check
    check (status in ('Disponível', 'Em operação', 'Em manutenção', 'Quebrada',
                       'Aguardando substituição', 'Substituído'));

-- Corrige eventuais linhas com o valor antigo 'Substituída'
update equipamentos set status = 'Substituído' where status = 'Substituída';

-- ------------------------------------------------------------
-- 2) Código só precisa ser único ENTRE equipamentos ativos.
--    Isso permite reaproveitar a numeração de um equipamento
--    "Substituído" (que fica inativo) em uma nova entrada.
-- ------------------------------------------------------------
alter table equipamentos drop constraint if exists equipamentos_codigo_key;
create unique index if not exists uq_equipamentos_codigo_ativo
    on equipamentos(codigo) where ativo = true;

-- ------------------------------------------------------------
-- 3) Motivos de quebra deixam de ser fixos no código e passam a
--    ser uma tabela editável em Configurações → Cadastros.
-- ------------------------------------------------------------
create table if not exists motivos_quebra (
    id uuid primary key default gen_random_uuid(),
    nome text not null unique,
    ativo boolean not null default true,
    created_at timestamptz not null default now()
);

insert into motivos_quebra (nome) values
    ('Rodas'), ('Garfo'), ('Sistema hidráulico'), ('Estrutura'),
    ('Alça/comando'), ('Elétrico'), ('Outro')
on conflict (nome) do nothing;

alter table motivos_quebra enable row level security;

-- A validação de motivo passa a ser feita pela aplicação (contra a tabela
-- acima), então o CHECK fixo antigo em ocorrencias precisa sair.
alter table ocorrencias drop constraint if exists ocorrencias_tipo_ocorrencia_check;

-- ------------------------------------------------------------
-- 4) Perfil Supervisor/Monitor: enxerga só o inventário e registra
--    quebras apenas do local vinculado ao seu cadastro.
-- ------------------------------------------------------------
alter table usuarios drop constraint if exists usuarios_perfil_check;
alter table usuarios add constraint usuarios_perfil_check
    check (perfil in ('Administrador', 'Supervisor'));

alter table usuarios add column if not exists local_id uuid references locais(id);

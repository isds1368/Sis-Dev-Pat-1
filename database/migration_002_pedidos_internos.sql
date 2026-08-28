-- ============================================================
-- MIGRAÇÃO — Pedidos Internos (chamados de substituição com fornecedor)
-- ============================================================
-- NÃO DESTRUTIVA: pode ser rodada em um banco que já está em produção,
-- com dados existentes. Não apaga nem recria nenhuma tabela já existente.
-- Execute este arquivo inteiro no SQL Editor do Supabase.
-- ============================================================

create table if not exists pedidos_internos (
    id uuid primary key default gen_random_uuid(),
    numero_interno text not null unique,
    numero_solicitacao_fornecedor text not null,
    dias_uteis_sla integer not null check (dias_uteis_sla > 0),
    data_abertura date not null default current_date,
    data_prevista date not null,
    data_atendimento date,
    status text not null default 'Aberto' check (status in ('Aberto', 'Atendido', 'Cancelado')),
    nota_sla numeric(5, 1),
    responsavel_abertura_id uuid references usuarios(id),
    responsavel_atendimento_id uuid references usuarios(id),
    created_at timestamptz not null default now()
);

create index if not exists idx_pedidos_internos_status on pedidos_internos(status);

-- Vincula pendências de substituição a um pedido interno (nullable: uma
-- pendência pode continuar avulsa, sem chamado formal com o fornecedor).
alter table substituicoes
    add column if not exists pedido_interno_id uuid references pedidos_internos(id);

create index if not exists idx_substituicoes_pedido_interno on substituicoes(pedido_interno_id);

-- Segurança: mesmo padrão do restante do sistema — só a chave service_role
-- (usada pelo backend Streamlit) acessa esta tabela.
alter table pedidos_internos enable row level security;

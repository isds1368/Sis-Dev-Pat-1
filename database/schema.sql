-- ============================================================
-- SISTEMA DE CONTROLE DE PALETEIRAS
-- Schema PostgreSQL / Supabase
-- ============================================================
-- Execute este arquivo INTEIRO no SQL Editor do Supabase, de uma vez.
-- Não contém nenhum campo financeiro (proibido pela regra de negócio).
--
-- ATENÇÃO: este script apaga (DROP) e recria as 7 tabelas do sistema
-- antes de criá-las de novo. Isso evita o erro
-- "column ... does not exist" causado por tabelas antigas/parciais que
-- ficaram com uma estrutura diferente da atual.
-- Se você já tem dados de produção nessas tabelas, faça um backup/export
-- antes de rodar — este script apaga tudo e começa do zero.
-- ============================================================

-- Extensão para geração de UUID
create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- LIMPEZA: remove qualquer versão anterior das tabelas, na ordem
-- inversa de dependência (cascade remove índices, triggers e FKs
-- que dependam delas automaticamente).
-- ------------------------------------------------------------
drop table if exists substituicoes cascade;
drop table if exists ocorrencias cascade;
drop table if exists distribuicao_planejada cascade;
drop table if exists movimentacoes cascade;
drop table if exists equipamentos cascade;
drop table if exists locais cascade;
drop table if exists usuarios cascade;
drop table if exists pedidos_internos cascade;
drop table if exists motivos_quebra cascade;
drop function if exists trg_set_updated_at cascade;

-- ------------------------------------------------------------
-- LOCAIS (Lojas, CDs, Estoques) — precisa existir antes de USUÁRIOS,
-- pois um Supervisor é vinculado a um local.
-- ------------------------------------------------------------
create table locais (
    id uuid primary key default gen_random_uuid(),
    nome text not null unique,
    tipo text not null default 'Loja' check (tipo in ('CD', 'Loja', 'Estoque', 'Manutencao')),
    ativo boolean not null default true,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- USUÁRIOS
-- Perfis:
--   Administrador — acesso completo.
--   Supervisor    — só enxerga o Inventário e registra Quebras do
--                    local vinculado em local_id.
-- ------------------------------------------------------------
create table usuarios (
    id uuid primary key default gen_random_uuid(),
    usuario text not null unique,
    senha_hash text not null,
    salt text not null,
    nome text not null,
    perfil text not null default 'Administrador' check (perfil in ('Administrador', 'Supervisor')),
    local_id uuid references locais(id),
    ativo boolean not null default true,
    -- Módulo de primeiro acesso: true quando a senha atual foi definida por
    -- outra pessoa (senha provisória) e ainda precisa ser trocada pelo
    -- próprio dono da conta antes de usar o sistema.
    deve_trocar_senha boolean not null default false,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- EQUIPAMENTOS (Paleteiras)
--
-- Ciclo de status relevante para substituição:
--   Quebrada
--     -> Aguardando substituição   (quando entra em um Pedido Interno)
--     -> Substituído               (quando o chamado é atendido na Chegada;
--                                    também marcado ativo=false: deixa de
--                                    contar como disponível em qualquer
--                                    hipótese, e libera seu código para
--                                    reaproveitamento em uma nova entrada)
-- ------------------------------------------------------------
create table equipamentos (
    id uuid primary key default gen_random_uuid(),
    codigo text not null,
    tipo text not null default 'Manual' check (tipo in ('Manual', 'Elétrica', 'Semi-elétrica')),
    propriedade text not null check (propriedade in ('Própria', 'Alugada')),
    fornecedor text,
    status text not null default 'Em operação'
        check (status in ('Em operação', 'Em manutenção', 'Quebrada',
                           'Aguardando substituição', 'Substituído')),
    localizacao_atual_id uuid references locais(id),
    data_chegada date not null,
    ativo boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Código único apenas ENTRE equipamentos ativos: permite reaproveitar a
-- numeração de um equipamento "Substituído" (inativo) numa nova entrada.
create unique index uq_equipamentos_codigo_ativo on equipamentos(codigo) where ativo = true;
create index idx_equipamentos_status on equipamentos(status);
create index idx_equipamentos_local on equipamentos(localizacao_atual_id);

-- ------------------------------------------------------------
-- MOVIMENTAÇÕES (histórico de deslocamento de cada equipamento)
-- ------------------------------------------------------------
create table movimentacoes (
    id uuid primary key default gen_random_uuid(),
    equipamento_id uuid not null references equipamentos(id),
    tipo_movimentacao text not null
        check (tipo_movimentacao in ('Chegada', 'Movimentação', 'Quebra', 'Substituição', 'Manutenção')),
    origem_id uuid references locais(id),
    destino_id uuid references locais(id),
    data_movimentacao date not null,
    responsavel_id uuid references usuarios(id),
    observacao text,
    created_at timestamptz not null default now()
);

create index idx_movimentacoes_equipamento on movimentacoes(equipamento_id);

-- ------------------------------------------------------------
-- DISTRIBUIÇÃO PLANEJADA (quantidade ideal por local)
-- ------------------------------------------------------------
create table distribuicao_planejada (
    id uuid primary key default gen_random_uuid(),
    local_id uuid not null references locais(id) unique,
    quantidade_planejada integer not null default 0,
    ativo boolean not null default true
);

-- ------------------------------------------------------------
-- MOTIVOS DE QUEBRA (editável em Configurações → Cadastros)
-- ------------------------------------------------------------
create table motivos_quebra (
    id uuid primary key default gen_random_uuid(),
    nome text not null unique,
    ativo boolean not null default true,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- OCORRÊNCIAS (quebras)
-- O motivo é validado pela aplicação contra motivos_quebra (tabela
-- editável), por isso não há CHECK fixo na coluna abaixo.
-- ------------------------------------------------------------
create table ocorrencias (
    id uuid primary key default gen_random_uuid(),
    equipamento_id uuid not null references equipamentos(id),
    local_id uuid references locais(id),
    tipo_ocorrencia text not null,
    descricao text,
    data_ocorrencia date not null,
    responsavel_id uuid references usuarios(id),
    status text not null default 'Aberta' check (status in ('Aberta', 'Resolvida')),
    created_at timestamptz not null default now()
);

create index idx_ocorrencias_equipamento on ocorrencias(equipamento_id);

-- ------------------------------------------------------------
-- PEDIDOS INTERNOS (chamados junto ao fornecedor p/ substituição)
-- ------------------------------------------------------------
create table pedidos_internos (
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

create index idx_pedidos_internos_status on pedidos_internos(status);

-- ------------------------------------------------------------
-- SUBSTITUIÇÕES
-- ------------------------------------------------------------
create table substituicoes (
    id uuid primary key default gen_random_uuid(),
    ocorrencia_id uuid references ocorrencias(id),
    equipamento_substituido_id uuid not null references equipamentos(id),
    equipamento_substituto_id uuid references equipamentos(id),
    local_id uuid references locais(id),
    pedido_interno_id uuid references pedidos_internos(id),
    motivo text default 'Quebra',
    data_solicitacao date not null default current_date,
    data_atendimento date,
    status text not null default 'Pendente' check (status in ('Pendente', 'Concluída', 'Cancelada')),
    observacao text,
    created_at timestamptz not null default now()
);

create index idx_substituicoes_status on substituicoes(status);
create index idx_substituicoes_pedido_interno on substituicoes(pedido_interno_id);

-- ------------------------------------------------------------
-- Trigger para manter updated_at de equipamentos em dia
-- ------------------------------------------------------------
create function trg_set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_updated_at
before update on equipamentos
for each row execute function trg_set_updated_at();

-- ============================================================
-- SEGURANÇA — ROW LEVEL SECURITY (RLS)
-- ============================================================
-- Habilita RLS em todas as tabelas e NÃO cria nenhuma política de acesso.
-- Resultado: as chaves "anon" e "authenticated" do Supabase ficam
-- completamente bloqueadas para ler/escrever qualquer linha via API REST
-- ou via o SDK do navegador.
--
-- O aplicativo Streamlit deve se conectar usando a chave "service_role"
-- (Project Settings → API → service_role secret). Essa chave roda apenas
-- no servidor (dentro de .streamlit/secrets.toml, nunca no navegador) e
-- ignora o RLS por definição — é assim que o app continua funcionando
-- normalmente enquanto qualquer outro acesso externo fica bloqueado.
--
-- Nunca use a chave service_role em código que roda no navegador do
-- usuário (JS, apps mobile, etc.) — aqui ela é segura porque o Streamlit
-- executa 100% no servidor.
-- ============================================================

alter table usuarios enable row level security;
alter table locais enable row level security;
alter table equipamentos enable row level security;
alter table movimentacoes enable row level security;
alter table distribuicao_planejada enable row level security;
alter table ocorrencias enable row level security;
alter table substituicoes enable row level security;
alter table pedidos_internos enable row level security;
alter table motivos_quebra enable row level security;

-- ------------------------------------------------------------
-- Dados iniciais de exemplo (opcional — remova se não quiser)
-- ------------------------------------------------------------
insert into motivos_quebra (nome) values
    ('Rodas'), ('Garfo'), ('Sistema hidráulico'), ('Estrutura'),
    ('Alça/comando'), ('Elétrico'), ('Outro');

insert into locais (nome, tipo) values
    ('CD Central', 'CD'),
    ('Loja A', 'Loja'),
    ('Loja B', 'Loja'),
    ('Loja C', 'Loja')
on conflict (nome) do nothing;

-- ============================================================
-- SISTEMA DE CONTROLE DE PALETEIRAS
-- Schema PostgreSQL / Supabase
-- ============================================================
-- Execute este arquivo inteiro no SQL Editor do Supabase.
-- Não contém nenhum campo financeiro (proibido pela regra de negócio).
-- ============================================================

-- Extensão para geração de UUID
create extension if not exists "pgcrypto";

-- ------------------------------------------------------------
-- USUÁRIOS
-- ------------------------------------------------------------
create table if not exists usuarios (
    id uuid primary key default gen_random_uuid(),
    usuario text not null unique,
    senha_hash text not null,
    salt text not null,
    nome text not null,
    perfil text not null default 'Administrador' check (perfil in ('Administrador')),
    ativo boolean not null default true,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- LOCAIS (Lojas, CDs, Estoques)
-- ------------------------------------------------------------
create table if not exists locais (
    id uuid primary key default gen_random_uuid(),
    nome text not null unique,
    tipo text not null default 'Loja' check (tipo in ('CD', 'Loja', 'Estoque', 'Manutencao')),
    ativo boolean not null default true,
    created_at timestamptz not null default now()
);

-- ------------------------------------------------------------
-- EQUIPAMENTOS (Paleteiras)
-- ------------------------------------------------------------
create table if not exists equipamentos (
    id uuid primary key default gen_random_uuid(),
    codigo text not null unique,
    tipo text not null default 'Manual' check (tipo in ('Manual', 'Elétrica', 'Semi-elétrica')),
    propriedade text not null check (propriedade in ('Própria', 'Alugada')),
    fornecedor text,
    status text not null default 'Disponível'
        check (status in ('Disponível', 'Em operação', 'Em manutenção', 'Quebrada', 'Substituída')),
    localizacao_atual_id uuid references locais(id),
    data_chegada date not null,
    ativo boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_equipamentos_status on equipamentos(status);
create index if not exists idx_equipamentos_local on equipamentos(localizacao_atual_id);

-- ------------------------------------------------------------
-- MOVIMENTAÇÕES (histórico de deslocamento de cada equipamento)
-- ------------------------------------------------------------
create table if not exists movimentacoes (
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

create index if not exists idx_movimentacoes_equipamento on movimentacoes(equipamento_id);

-- ------------------------------------------------------------
-- DISTRIBUIÇÃO PLANEJADA (quantidade ideal por local)
-- ------------------------------------------------------------
create table if not exists distribuicao_planejada (
    id uuid primary key default gen_random_uuid(),
    local_id uuid not null references locais(id) unique,
    quantidade_planejada integer not null default 0,
    ativo boolean not null default true
);

-- ------------------------------------------------------------
-- OCORRÊNCIAS (quebras)
-- ------------------------------------------------------------
create table if not exists ocorrencias (
    id uuid primary key default gen_random_uuid(),
    equipamento_id uuid not null references equipamentos(id),
    local_id uuid references locais(id),
    tipo_ocorrencia text not null
        check (tipo_ocorrencia in ('Rodas', 'Garfo', 'Sistema hidráulico', 'Estrutura', 'Alça/comando', 'Elétrico', 'Outro')),
    descricao text,
    data_ocorrencia date not null,
    responsavel_id uuid references usuarios(id),
    status text not null default 'Aberta' check (status in ('Aberta', 'Resolvida')),
    created_at timestamptz not null default now()
);

create index if not exists idx_ocorrencias_equipamento on ocorrencias(equipamento_id);

-- ------------------------------------------------------------
-- SUBSTITUIÇÕES
-- ------------------------------------------------------------
create table if not exists substituicoes (
    id uuid primary key default gen_random_uuid(),
    ocorrencia_id uuid references ocorrencias(id),
    equipamento_substituido_id uuid not null references equipamentos(id),
    equipamento_substituto_id uuid references equipamentos(id),
    local_id uuid references locais(id),
    motivo text default 'Quebra',
    data_solicitacao date not null default current_date,
    data_atendimento date,
    status text not null default 'Pendente' check (status in ('Pendente', 'Concluída', 'Cancelada')),
    observacao text,
    created_at timestamptz not null default now()
);

create index if not exists idx_substituicoes_status on substituicoes(status);

-- ------------------------------------------------------------
-- Trigger para manter updated_at de equipamentos em dia
-- ------------------------------------------------------------
create or replace function trg_set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists set_updated_at on equipamentos;
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

-- ------------------------------------------------------------
-- Dados iniciais de exemplo (opcional — remova se não quiser)
-- ------------------------------------------------------------
insert into locais (nome, tipo) values
    ('CD Central', 'CD'),
    ('Loja A', 'Loja'),
    ('Loja B', 'Loja'),
    ('Loja C', 'Loja')
on conflict (nome) do nothing;

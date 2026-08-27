# Controle de Paleteiras

Sistema web operacional para controle de paleteiras: chegada, distribuição,
movimentação, quebras e substituições. Não possui nenhum controle financeiro.

Stack: **Python + Streamlit + Supabase (PostgreSQL) + GitHub**.

---

## 1. Estrutura do projeto

```text
projeto_paleteiras/
├── app.py                     # ponto de entrada (login + navegação + roteamento)
├── requirements.txt
├── README.md
├── .gitignore
│
├── database/
│   └── schema.sql             # script completo para rodar no Supabase
│
├── .streamlit/
│   ├── config.toml            # tema visual
│   └── secrets.toml.example   # modelo de credenciais (copie para secrets.toml)
│
├── assets/
│   └── style.css              # design system (cores de status, cards, sidebar)
│
├── pages_app/                 # páginas da aplicação (chamadas por app.py)
│   ├── dashboard.py
│   ├── inventario.py
│   ├── chegada.py
│   ├── movimentacao.py
│   ├── distribuicao.py
│   ├── quebra.py
│   ├── substituicoes.py
│   └── historico.py
│
├── services/                  # regras de negócio + acesso ao Supabase
│   ├── equipamentos.py
│   ├── locais.py
│   ├── movimentacoes.py
│   ├── distribuicao.py
│   ├── ocorrencias.py
│   └── substituicoes.py
│
├── utils/
│   ├── database.py            # cliente Supabase
│   ├── auth.py                # login + hash de senha (PBKDF2)
│   └── helpers.py             # badges de status, tempo de uso, formatação
│
└── scripts/
    └── criar_usuario_admin.py # CLI para criar o primeiro usuário
```

> Nota sobre a pasta `pages_app/`: ela **não** usa o sistema nativo de
> multipágina do Streamlit (pasta `pages/`), porque isso geraria uma barra
> lateral padrão do Streamlit, fora do design system do projeto. Em vez
> disso, `app.py` controla a navegação manualmente via `st.session_state`,
> permitindo total controle visual da sidebar (grupos, botões ativos, etc).

---

## 2. Passo a passo — Supabase

1. Crie um projeto em [supabase.com](https://supabase.com).
2. Abra **SQL Editor** e execute todo o conteúdo de `database/schema.sql`.
3. Em **Project Settings → API**, copie:
   - `Project URL` → `SUPABASE_URL`
   - `anon public key` (ou `service_role`, se preferir acesso irrestrito do backend) → `SUPABASE_KEY`

---

## 3. Configuração local

```bash
git clone <seu-repositorio>
cd projeto_paleteiras

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edite .streamlit/secrets.toml com SUPABASE_URL e SUPABASE_KEY
```

### Criar o primeiro usuário administrador

```bash
export SUPABASE_URL="https://SEU-PROJETO.supabase.co"
export SUPABASE_KEY="sua-chave"
python scripts/criar_usuario_admin.py
```

### Rodar localmente

```bash
streamlit run app.py
```

---

## 4. Deploy (Streamlit Community Cloud ou similar)

1. Suba o projeto para o GitHub (o `.gitignore` já impede o envio de `secrets.toml`).
2. Conecte o repositório na plataforma de hospedagem Streamlit.
3. Em **Secrets** da plataforma, cole o mesmo conteúdo de `secrets.toml`:
   ```toml
   SUPABASE_URL = "https://SEU-PROJETO.supabase.co"
   SUPABASE_KEY = "sua-chave"
   ```
4. Defina `app.py` como arquivo principal.

---

## 5. Regras de negócio implementadas

| Regra | Onde está |
|---|---|
| Código de equipamento único | `services/equipamentos.py` (`codigo_existe`) validado em `pages_app/chegada.py` |
| Toda alteração de local gera movimentação | `services/movimentacoes.py` (`mover_equipamento`, `registrar_chegada`) |
| Histórico nunca é apagado | Nenhuma rotina de `delete` existe para `movimentacoes` |
| Quebrado / em manutenção não conta como operacional | `services/distribuicao.py` (`visao_distribuicao`) |
| Déficit = planejado − operacional | `utils/helpers.py` (`calcular_deficit`) |
| Déficit por quebra cria substituição pendente automaticamente | `services/ocorrencias.py` (`registrar_quebra` → `_criar_substituicao_pendente`) |
| Destino de cada equipamento é definido manualmente na chegada | `pages_app/chegada.py` (um seletor de destino por equipamento) |
| Sem valores financeiros | Nenhuma tabela ou campo do schema contém preço/custo/valor |

---

## 6. Segurança — o que foi verificado e corrigido

Uma revisão de segurança foi feita neste código. Resumo do que foi encontrado e corrigido:

| Risco | Situação | Correção |
|---|---|---|
| XSS armazenado (HTML/JS malicioso em Código, Fornecedor, Nome de usuário exibidos sem escapar) | **Encontrado** em `dashboard.py`, `inventario.py`, `movimentacao.py` e no nome de usuário na sidebar (`app.py`) | Todo texto vindo do banco agora passa por `utils.helpers.esc()` antes de entrar em HTML (`unsafe_allow_html=True`) |
| Códigos de equipamento com caracteres arbitrários | Campo livre sem validação | `services/equipamentos.py` valida com regex (`A-Z a-z 0-9 - _`, até 30 caracteres) |
| Login/senha fracos | Sem regra mínima | `utils/auth.py` exige login com formato controlado e senha com 8+ caracteres, maiúscula, minúscula e número |
| Vazamento de dados via API pública do Supabase | Sem RLS, a chave `anon` conseguiria ler/escrever qualquer tabela diretamente pela API REST, contornando o login do app | `database/schema.sql` habilita **Row Level Security em todas as tabelas sem políticas** — a chave `anon` fica bloqueada; o app passa a usar a chave `service_role` (fica só em `secrets.toml`, nunca no navegador) |
| Enumeração de usuário / força bruta no login | Resposta instantânea permitia tentar muitos logins rapidamente | `autenticar()` adiciona um pequeno atraso constante em tentativas inválidas |
| Senhas em texto puro | Nunca ocorreu — já usava PBKDF2-HMAC-SHA256 (200.000 iterações) + salt único por usuário | Mantido; hash e salt nunca são retornados por `listar_usuarios()` |
| Segredos no repositório | `SUPABASE_URL`/`SUPABASE_KEY` já vinham de `st.secrets`, nunca hardcoded | Confirmado por varredura (`grep`); `.gitignore` cobre `secrets.toml` |
| SQL Injection | O SDK do Supabase usa consultas parametrizadas (PostgREST), nenhuma string é concatenada em SQL | Confirmado por varredura no código |

### Ação que você precisa tomar no Supabase

1. Rode o `schema.sql` atualizado (ou apenas os comandos `alter table ... enable row level security;` do final, se o banco já existir).
2. Em **Project Settings → API**, copie a chave **`service_role`** (não a `anon`) para `SUPABASE_KEY` em `secrets.toml`.
3. Nunca coloque a chave `service_role` em nenhum lugar que rode no navegador — aqui ela é segura porque o Streamlit roda inteiramente no servidor.

## 7. Como dar acesso a outras pessoas

Agora existe uma tela **Configurações → Usuários** dentro do próprio app (não precisa mais rodar o script por terminal):

- Qualquer pessoa logada pode criar um novo login ali, definindo usuário, nome e uma senha provisória.
- Contas nunca são apagadas, apenas **desativadas** (o histórico de quem registrou cada movimentação continua íntegro).
- Cada pessoa pode trocar a própria senha na mesma tela, informando a senha atual.
- O script `scripts/criar_usuario_admin.py` continua funcionando e é útil apenas para criar o **primeiro** usuário, antes de existir alguém logado para usar a tela.

> O sistema hoje tem um único perfil (Administrador) — ou seja, todas as pessoas com login têm as mesmas permissões dentro do app. Se no futuro você quiser perfis com permissões diferentes (ex.: alguém que só consulta e não registra quebras), isso pode ser adicionado depois sem redesenhar o sistema.

## 8. O que este sistema propositalmente não faz

Financeiro, custos, contratos, compras, faturamento, ordens de serviço,
integração com ERP, previsão de demanda, depreciação ou qualquer módulo que
não ajude diretamente a saber **onde está cada paleteira, em que status, e o
que precisa ser feito com ela**.

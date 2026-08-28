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
│   ├── schema.sql                              # instalação nova (reset total)
│   ├── migration_002_pedidos_internos.sql      # migração incremental
│   ├── migration_003_status_perfis_cadastros.sql  # migração incremental
│   └── migration_004_remove_status_disponivel.sql # migração incremental
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
│   ├── pedidos_internos.py
│   ├── historico.py
│   ├── usuarios.py
│   └── cadastros.py
│
├── services/                  # regras de negócio + acesso ao Supabase
│   ├── equipamentos.py
│   ├── locais.py
│   ├── movimentacoes.py
│   ├── distribuicao.py
│   ├── ocorrencias.py
│   ├── substituicoes.py
│   ├── pedidos_internos.py
│   └── motivos_quebra.py
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

**Instalação nova:** execute `database/schema.sql` inteiro no SQL Editor.

**Banco já existente** (você já tinha rodado uma versão anterior deste projeto): **não** rode o `schema.sql` de novo — ele apaga as tabelas. Rode as migrações incrementais na ordem:
1. `database/migration_002_pedidos_internos.sql`
2. `database/migration_003_status_perfis_cadastros.sql`
3. `database/migration_004_remove_status_disponivel.sql`

Nenhuma delas apaga dados existentes.

1. Crie um projeto em [supabase.com](https://supabase.com) (se ainda não tiver um).
2. Abra **SQL Editor** e execute o script apropriado, conforme acima.
3. Em **Project Settings → API**, copie:
   - `Project URL` → `SUPABASE_URL`
   - `service_role secret key` → `SUPABASE_KEY` (veja a seção de Segurança abaixo sobre por que usar essa chave e não a `anon`)

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

## 8. Pedidos Internos (chamados junto ao fornecedor)

Fluxo completo para controlar o prazo de reposição de equipamentos quebrados junto ao fornecedor.

### Como abrir um pedido
Em **Substituições → Pedidos Internos**, preencha manualmente:
1. Número da solicitação aberta junto ao fornecedor;
2. Prazo em dias úteis para atendimento (SLA);
3. Quais equipamentos quebrados serão substituídos.

O sistema gera automaticamente um número interno sequencial (`PI-0001`, `PI-0002`...) e calcula o prazo previsto somando os dias úteis à data de abertura (sábados e domingos não contam; feriados não são considerados, para manter o cálculo simples).

### Cards e popup
Pedidos em aberto aparecem como cards com número interno, data de criação e SLA previsto. Clicar em "Ver detalhes" abre um popup flutuante (`st.dialog`) com todos os equipamentos do pedido e o status de cada um.

### Nota de SLA (ponderada)
Quando o pedido é totalmente atendido, uma nota de 0 a 100 é calculada:

- **No prazo:** nota = 100.
- **Com atraso:** `nota = 100 − (dias úteis de atraso × 8 × multiplicador)`, onde `multiplicador = 1 + (quantidade de equipamentos do pedido − 1) × 0,15`.

Ou seja, dois pesos entram na conta — cada dia útil de atraso pesa 8 pontos isoladamente, e pedidos maiores (mais equipamentos parados) são penalizados proporcionalmente mais por dia de atraso, porque o impacto operacional é maior. A fórmula está documentada e isolada em `services/pedidos_internos.py` (`calcular_nota_sla`), fácil de recalibrar depois se os pesos precisarem mudar.

### Como o pedido é "atendido"
Não existe um botão de "concluir pedido". Ele só é encerrado **na tela de Chegada**, quando os equipamentos novos chegam de fato:

1. Ao registrar uma nova chegada, o sistema primeiro pergunta a qual pedido interno ela se refere (ou "Nenhum", para chegadas sem vínculo).
2. Ao escolher um pedido, o sistema mostra o número do chamado, os equipamentos que serão substituídos e quantos equipamentos quebrados pendentes existem em cada setor.
3. Só depois disso os campos de chegada (data, quantidade, tipo etc.) e o avanço para destino são liberados.
4. Conforme você define o destino de cada novo equipamento, o saldo de pendências por setor é atualizado ao vivo na tela.
5. Ao salvar, cada equipamento novo é automaticamente casado com a pendência mais antiga daquele setor dentro do pedido. Quando o último item é resolvido, o pedido muda para "Atendido", a nota de SLA é calculada e ele passa para o histórico.

### Histórico
Pedidos concluídos aparecem em tabela, com data de abertura, prazo, data real de atendimento, dias de atraso e nota de SLA — nunca são apagados.

## 9. Ciclo de vida do equipamento quebrado

```
Quebrada
   → Aguardando substituição   (ao entrar em um Pedido Interno)
   → Substituído                (quando o chamado é atendido na Chegada)
```

Um equipamento **"Substituído"** é automaticamente desativado (`ativo = false`) e nunca mais aparece como disponível em nenhuma tela — nem em Movimentar, nem em Registrar Quebra, nem em novos Pedidos Internos — em nenhuma hipótese. A única forma de "reaproveitar" aquele número é registrar uma **nova entrada** (nova chegada) com o mesmo código: o sistema libera o código automaticamente para reuso assim que o equipamento antigo é desativado, mas cria um registro novo — o antigo permanece no banco, intacto, como histórico.

Na tela de **Distribuição**, a coluna "Quebradas" soma equipamentos em `Quebrada` **e** `Aguardando substituição`, já que ambos representam equipamentos fora de operação por causa de uma quebra.

## 10. Perfis de usuário

| Perfil | Acesso |
|---|---|
| **Administrador** | Todas as telas do sistema. |
| **Supervisor / Monitor** | Apenas **Inventário** (só do local vinculado ao seu cadastro) e **Registrar Quebra** (só de equipamentos daquele local). Nenhuma outra tela aparece na navegação, e o sistema bloqueia o acesso direto mesmo que a página seja forçada via estado da sessão. |

O local do Supervisor é definido na criação do acesso, em **Configurações → Usuários**.

## 11. Cadastros (Locais e Motivos de Quebra)

Em **Configurações → Cadastros**, um Administrador pode criar novos locais e novos motivos de quebra, além de editar os existentes (renomear, ativar/desativar) — sem precisar mexer em código. Motivos de quebra deixaram de ser uma lista fixa e passaram a vir da tabela `motivos_quebra`.

## 12. O que este sistema propositalmente não faz

Financeiro, custos, contratos, compras, faturamento, ordens de serviço,
integração com ERP, previsão de demanda, depreciação ou qualquer módulo que
não ajude diretamente a saber **onde está cada paleteira, em que status, e o
que precisa ser feito com ela**.

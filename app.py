import streamlit as st

from utils.auth import autenticar, usuario_logado, logout, existe_usuario, criar_usuario
from utils.helpers import esc
from pages_app import (
    dashboard,
    inventario,
    chegada,
    movimentacao,
    distribuicao,
    quebra,
    substituicoes,
    historico,
    usuarios,
)

st.set_page_config(
    page_title="Controle de Paleteiras",
    page_icon="🟦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def carregar_css():
    with open("assets/style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


carregar_css()

# ------------------------------------------------------------
# TELA DE PRIMEIRO ACESSO (só aparece se não houver nenhum usuário)
# ------------------------------------------------------------
def tela_primeiro_acesso():
    st.markdown(
        """
        <div style="max-width:420px; margin: 5rem auto 0 auto;">
            <div class="page-title" style="text-align:center;">Controle de Paleteiras</div>
            <div class="page-subtitle" style="text-align:center;">
                Primeiro acesso — crie o usuário administrador
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_esq, col_meio, col_dir = st.columns([1, 1.4, 1])
    with col_meio:
        st.info(
            "Nenhum usuário cadastrado ainda. Crie o primeiro acesso "
            "(Administrador) para começar a usar o sistema."
        )
        with st.form("form_primeiro_acesso"):
            login = st.text_input("Login (usuário)", placeholder="ex: admin")
            nome = st.text_input("Nome completo")
            senha = st.text_input("Senha", type="password")
            senha_confirma = st.text_input("Confirmar senha", type="password")

            st.caption(
                "A senha deve ter no mínimo 8 caracteres, com letras "
                "maiúsculas, minúsculas e ao menos um número."
            )

            criar = st.form_submit_button("Criar usuário administrador")

            if criar:
                if not login or not nome:
                    st.error("Preencha login e nome.")
                elif senha != senha_confirma:
                    st.error("As senhas não coincidem.")
                else:
                    try:
                        criar_usuario(usuario=login, senha=senha, nome=nome)
                        st.success("Usuário administrador criado com sucesso. Faça login abaixo.")
                        st.rerun()
                    except ValueError as erro:
                        st.error(str(erro))


# ------------------------------------------------------------
# TELA DE LOGIN
# ------------------------------------------------------------
def tela_login():
    st.markdown(
        """
        <div style="max-width:380px; margin: 6rem auto 0 auto;">
            <div class="page-title" style="text-align:center;">Controle de Paleteiras</div>
            <div class="page-subtitle" style="text-align:center;">Acesso ao sistema</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_esq, col_meio, col_dir = st.columns([1, 1.2, 1])
    with col_meio:
        with st.form("form_login"):
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")

            if entrar:
                registro = autenticar(usuario.strip(), senha)
                if registro:
                    st.session_state["usuario_logado"] = registro
                    st.session_state["pagina_atual"] = "Dashboard"
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")


# ------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------
NAV_ESTRUTURA = [
    ("Dashboard", None),
    ("Inventário", None),
    ("Movimentações", [
        "Registrar Chegada",
        "Movimentar Equipamento",
    ]),
    ("Distribuição", None),
    ("Quebras", [
        "Registrar Quebra",
    ]),
    ("Substituições", None),
    ("Histórico", None),
    ("Configurações", [
        "Usuários",
    ]),
]

PAGINAS_RENDER = {
    "Dashboard": dashboard.render,
    "Inventário": inventario.render,
    "Registrar Chegada": chegada.render,
    "Movimentar Equipamento": movimentacao.render,
    "Distribuição": distribuicao.render,
    "Registrar Quebra": quebra.render,
    "Substituições": substituicoes.render,
    "Histórico": historico.render,
    "Usuários": usuarios.render,
}


def nav_button(label, chave_pagina, indent=False):
    ativo = st.session_state.get("pagina_atual") == chave_pagina
    if st.button(
        label,
        key=f"nav_{chave_pagina}",
        use_container_width=True,
        type="primary" if ativo else "secondary",
    ):
        st.session_state["pagina_atual"] = chave_pagina
        st.rerun()


def sidebar():
    usuario = usuario_logado()
    with st.sidebar:
        # Nome do usuário vem do banco (definido no cadastro) e é escapado
        # antes de entrar em HTML bruto — nunca confiar em texto armazenado.
        st.markdown(
            f"""
            <div class="sidebar-brand">
                Controle de Paleteiras
                <span>{esc(usuario['nome'])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for titulo, subitens in NAV_ESTRUTURA:
            if subitens is None:
                nav_button(titulo, titulo)
            else:
                st.markdown(f'<div class="sidebar-section-label">{titulo}</div>', unsafe_allow_html=True)
                for sub in subitens:
                    nav_button(sub, sub)

        st.markdown("---")
        if st.button("Sair", use_container_width=True):
            logout()
            st.rerun()


# ------------------------------------------------------------
# ROTEAMENTO PRINCIPAL
# ------------------------------------------------------------
def main():
    if not usuario_logado():
        # Antes de mostrar o login, verifica se já existe algum usuário.
        # Se não existir, obriga a criação do primeiro administrador —
        # evita depender do script de terminal para o primeiro acesso.
        if not existe_usuario():
            tela_primeiro_acesso()
        else:
            tela_login()
        return

    if "pagina_atual" not in st.session_state:
        st.session_state["pagina_atual"] = "Dashboard"

    sidebar()

    pagina = st.session_state["pagina_atual"]
    render_fn = PAGINAS_RENDER.get(pagina, dashboard.render)
    render_fn()


if __name__ == "__main__":
    main()

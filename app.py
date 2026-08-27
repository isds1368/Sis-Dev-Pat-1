import streamlit as st

from utils.auth import autenticar, usuario_logado, logout
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

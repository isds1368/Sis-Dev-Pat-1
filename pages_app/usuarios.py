import pandas as pd
import streamlit as st

from utils.auth import (
    usuario_logado,
    listar_usuarios,
    criar_usuario,
    definir_status_usuario,
    alterar_propria_senha,
)
from utils.helpers import formatar_data_br


def render():
    st.markdown('<div class="page-title">Usuários</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Controle de quem tem acesso ao sistema</div>',
        unsafe_allow_html=True,
    )

    eu = usuario_logado()

    # ---------------- Criar novo acesso ----------------
    st.markdown('<div class="section-title">Conceder acesso a uma nova pessoa</div>', unsafe_allow_html=True)
    with st.form("form_novo_usuario", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            novo_login = st.text_input(
                "Login (usuário)", placeholder="ex: joao.silva", max_chars=40
            )
        with c2:
            novo_nome = st.text_input("Nome completo", max_chars=100)

        c3, c4 = st.columns(2)
        with c3:
            nova_senha = st.text_input("Senha provisória", type="password")
        with c4:
            nova_senha_confirma = st.text_input("Confirmar senha", type="password")

        st.caption(
            "A senha deve ter no mínimo 8 caracteres, com letras maiúsculas, "
            "minúsculas e ao menos um número. Oriente a pessoa a alterá-la no "
            "primeiro acesso, em 'Alterar minha senha' abaixo."
        )

        criar = st.form_submit_button("Criar acesso")

        if criar:
            if not novo_login or not novo_nome:
                st.error("Preencha login e nome.")
            elif nova_senha != nova_senha_confirma:
                st.error("As senhas não coincidem.")
            else:
                try:
                    criar_usuario(usuario=novo_login, senha=nova_senha, nome=novo_nome)
                    st.success(f"Acesso criado para {novo_nome} (login: {novo_login}).")
                    st.rerun()
                except ValueError as erro:
                    st.error(str(erro))

    # ---------------- Lista de usuários ----------------
    st.markdown('<div class="section-title">Pessoas com acesso</div>', unsafe_allow_html=True)
    usuarios = listar_usuarios()

    if usuarios:
        for u in usuarios:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"**{u['nome']}**")
                    st.caption(f"Login: {u['usuario']}")
                with c2:
                    st.caption(f"Perfil: {u['perfil']} · Desde {formatar_data_br(u['created_at'])}")
                    st.caption("✅ Ativo" if u["ativo"] else "🚫 Acesso desativado")
                with c3:
                    if u["id"] == eu["id"]:
                        st.caption("Você")
                    elif u["ativo"]:
                        if st.button("Desativar", key=f"desativar_{u['id']}"):
                            definir_status_usuario(u["id"], ativo=False)
                            st.rerun()
                    else:
                        if st.button("Reativar", key=f"reativar_{u['id']}"):
                            definir_status_usuario(u["id"], ativo=True)
                            st.rerun()
    st.caption(
        "Por segurança, contas nunca são apagadas — apenas desativadas. "
        "Isso preserva o histórico de quem registrou cada movimentação."
    )

    # ---------------- Alterar a própria senha ----------------
    st.markdown("---")
    st.markdown('<div class="section-title">Alterar minha senha</div>', unsafe_allow_html=True)
    with st.form("form_alterar_senha", clear_on_submit=True):
        senha_atual = st.text_input("Senha atual", type="password")
        senha_nova = st.text_input("Nova senha", type="password")
        senha_nova_confirma = st.text_input("Confirmar nova senha", type="password")
        alterar = st.form_submit_button("Alterar senha")

        if alterar:
            if senha_nova != senha_nova_confirma:
                st.error("As senhas novas não coincidem.")
            else:
                ok, mensagem = alterar_propria_senha(eu["id"], senha_atual, senha_nova)
                if ok:
                    st.success(mensagem)
                else:
                    st.error(mensagem)

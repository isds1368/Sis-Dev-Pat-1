import streamlit as st

from services import locais as svc_locais
from services import motivos_quebra as svc_motivos

TIPOS_LOCAL = ["CD", "Loja", "Estoque", "Manutencao"]


def _aba_locais():
    st.markdown('<div class="section-title">Novo local</div>', unsafe_allow_html=True)
    with st.form("form_novo_local", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nome = st.text_input("Nome do local", max_chars=100)
        with c2:
            tipo = st.selectbox("Tipo", TIPOS_LOCAL)
        criar = st.form_submit_button("Cadastrar local")

        if criar:
            try:
                svc_locais.criar_local(nome=nome, tipo=tipo)
                st.success(f"Local '{nome}' cadastrado.")
                st.rerun()
            except ValueError as erro:
                st.error(str(erro))

    st.markdown('<div class="section-title">Locais cadastrados</div>', unsafe_allow_html=True)
    for local in svc_locais.listar_locais(apenas_ativos=False):
        with st.container(border=True):
            with st.form(f"form_editar_local_{local['id']}"):
                c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                with c1:
                    novo_nome = st.text_input("Nome", value=local["nome"], key=f"nome_local_{local['id']}", max_chars=100)
                with c2:
                    novo_tipo = st.selectbox(
                        "Tipo", TIPOS_LOCAL, index=TIPOS_LOCAL.index(local["tipo"]) if local["tipo"] in TIPOS_LOCAL else 0,
                        key=f"tipo_local_{local['id']}",
                    )
                with c3:
                    novo_ativo = st.selectbox(
                        "Situação", ["Ativo", "Inativo"],
                        index=0 if local["ativo"] else 1,
                        key=f"ativo_local_{local['id']}",
                    )
                with c4:
                    st.write("")
                    salvar = st.form_submit_button("Salvar")

                if salvar:
                    svc_locais.editar_local(
                        local["id"], nome=novo_nome, tipo=novo_tipo, ativo=(novo_ativo == "Ativo")
                    )
                    st.success(f"Local '{novo_nome}' atualizado.")
                    st.rerun()


def _aba_motivos():
    st.markdown('<div class="section-title">Novo motivo de quebra</div>', unsafe_allow_html=True)
    with st.form("form_novo_motivo", clear_on_submit=True):
        nome = st.text_input("Nome do motivo", placeholder="Ex: Bateria", max_chars=60)
        criar = st.form_submit_button("Cadastrar motivo")

        if criar:
            try:
                svc_motivos.criar(nome)
                st.success(f"Motivo '{nome}' cadastrado.")
                st.rerun()
            except ValueError as erro:
                st.error(str(erro))

    st.markdown('<div class="section-title">Motivos cadastrados</div>', unsafe_allow_html=True)
    for motivo in svc_motivos.listar(apenas_ativos=False):
        with st.container(border=True):
            with st.form(f"form_editar_motivo_{motivo['id']}"):
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    novo_nome = st.text_input("Nome", value=motivo["nome"], key=f"nome_motivo_{motivo['id']}", max_chars=60)
                with c2:
                    novo_ativo = st.selectbox(
                        "Situação", ["Ativo", "Inativo"],
                        index=0 if motivo["ativo"] else 1,
                        key=f"ativo_motivo_{motivo['id']}",
                    )
                with c3:
                    st.write("")
                    salvar = st.form_submit_button("Salvar")

                if salvar:
                    svc_motivos.editar(motivo["id"], nome=novo_nome, ativo=(novo_ativo == "Ativo"))
                    st.success(f"Motivo '{novo_nome}' atualizado.")
                    st.rerun()


def render():
    st.markdown('<div class="page-title">Cadastros</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Locais e motivos de quebra usados no restante do sistema</div>',
        unsafe_allow_html=True,
    )

    aba_locais, aba_motivos = st.tabs(["Locais", "Motivos de Quebra"])
    with aba_locais:
        _aba_locais()
    with aba_motivos:
        _aba_motivos()

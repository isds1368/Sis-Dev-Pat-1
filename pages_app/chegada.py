from datetime import date

import streamlit as st

from services import equipamentos as svc_equip
from services import locais as svc_locais
from services import movimentacoes as svc_mov
from utils.auth import usuario_logado


def render():
    st.markdown('<div class="page-title">Registrar Chegada</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Cadastre novos equipamentos e defina o destino de cada um</div>',
        unsafe_allow_html=True,
    )

    locais = svc_locais.listar_locais()
    if not locais:
        st.warning("Cadastre ao menos um local antes de registrar uma chegada.")
        return
    nomes_locais = {l["nome"]: l["id"] for l in locais}

    # Etapa 1 — dados gerais da chegada
    with st.form("form_dados_chegada"):
        st.markdown("**Dados da chegada**")
        c1, c2, c3 = st.columns(3)
        with c1:
            data_chegada = st.date_input("Data da chegada", value=date.today(), format="DD/MM/YYYY")
        with c2:
            quantidade = st.number_input("Quantidade", min_value=1, max_value=100, value=1, step=1)
        with c3:
            tipo = st.selectbox("Tipo", svc_equip.TIPOS_EQUIPAMENTO)

        c4, c5 = st.columns(2)
        with c4:
            propriedade = st.selectbox("Propriedade", svc_equip.PROPRIEDADES)
        with c5:
            fornecedor = st.text_input("Fornecedor", placeholder="Ex: Fornecedor X", max_chars=100)

        avancar = st.form_submit_button("Avançar para definição de destino →")

        if avancar:
            st.session_state["chegada_config"] = {
                "data_chegada": data_chegada.isoformat(),
                "quantidade": int(quantidade),
                "tipo": tipo,
                "propriedade": propriedade,
                "fornecedor": fornecedor,
            }
            st.session_state.pop("chegada_codigos", None)

    config = st.session_state.get("chegada_config")
    if not config:
        return

    st.markdown("---")
    st.markdown('<div class="section-title">Definir código e destino de cada equipamento</div>', unsafe_allow_html=True)
    st.caption("Cada equipamento pode ter um destino diferente — a decisão é sempre manual.")

    sugestao_base = svc_equip.proximo_codigo_sugerido()
    sugestao_num = int(sugestao_base.split("-")[1])

    with st.form("form_destinos"):
        destinos = []
        for i in range(config["quantidade"]):
            codigo_sugerido = f"PAL-{sugestao_num + i:03d}"
            colc, cold = st.columns([1, 2])
            with colc:
                codigo = st.text_input(f"Código #{i+1}", value=codigo_sugerido, key=f"codigo_{i}")
            with cold:
                destino_nome = st.selectbox(
                    f"Destino de {codigo_sugerido}",
                    options=list(nomes_locais.keys()),
                    key=f"destino_{i}",
                )
            destinos.append((codigo, destino_nome))

        confirmar = st.form_submit_button("Salvar chegada")

        if confirmar:
            codigos_informados = [c.strip() for c, _ in destinos]

            invalidos = [c for c in codigos_informados if not svc_equip.codigo_valido(c)]
            if invalidos:
                st.error(
                    "Códigos inválidos: "
                    f"{', '.join(invalidos)}. "
                    "Use apenas letras, números, hífen e underscore (até 30 caracteres)."
                )
                return

            if len(set(codigos_informados)) != len(codigos_informados):
                st.error("Existem códigos duplicados na lista. Corrija antes de salvar.")
                return

            duplicados_no_banco = [c for c in codigos_informados if svc_equip.codigo_existe(c)]
            if duplicados_no_banco:
                st.error(f"Estes códigos já existem no sistema: {', '.join(duplicados_no_banco)}")
                return

            usuario = usuario_logado()
            responsavel_id = usuario["id"] if usuario else None

            criados = []
            for codigo, destino_nome in destinos:
                destino_id = nomes_locais[destino_nome]
                local_info = next(l for l in locais if l["id"] == destino_id)

                # Regra 14: CD/Estoque = Disponível; unidade operacional = Em operação
                status_destino = (
                    svc_equip.STATUS_DISPONIVEL
                    if local_info["tipo"] in ("CD", "Estoque")
                    else svc_equip.STATUS_OPERACIONAL
                )

                equipamento = svc_mov.registrar_chegada(
                    codigo=codigo,
                    tipo=config["tipo"],
                    propriedade=config["propriedade"],
                    fornecedor=config["fornecedor"],
                    data_chegada=config["data_chegada"],
                    destino_id=destino_id,
                    status_destino=status_destino,
                    responsavel_id=responsavel_id,
                )
                criados.append((codigo, destino_nome, status_destino))

            st.success(f"{len(criados)} equipamento(s) registrado(s) com sucesso.")
            for codigo, destino_nome, status_destino in criados:
                st.write(f"- **{codigo}** → {destino_nome} ({status_destino})")

            st.session_state.pop("chegada_config", None)

from datetime import date

import streamlit as st

from services import equipamentos as svc_equip
from services import locais as svc_locais
from services import movimentacoes as svc_mov
from utils.auth import usuario_logado
from utils.helpers import status_badge, esc


def render():
    st.markdown('<div class="page-title">Movimentar Equipamento</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Transferência de um equipamento entre locais</div>',
        unsafe_allow_html=True,
    )

    equipamentos = [
        e for e in svc_equip.listar_equipamentos() if e["status"] not in svc_equip.STATUS_FORA_DE_OPERACAO
    ]
    locais = svc_locais.listar_locais()
    locais_map = svc_locais.mapa_id_para_nome()

    if not equipamentos:
        st.info("Não há equipamentos disponíveis para movimentação.")
        return
    if not locais:
        st.warning("Cadastre ao menos um local antes de movimentar equipamentos.")
        return

    codigos_map = {e["codigo"]: e for e in equipamentos}

    with st.form("form_movimentacao"):
        codigo_selecionado = st.selectbox("Equipamento", options=list(codigos_map.keys()))
        equipamento = codigos_map[codigo_selecionado]
        origem_nome = locais_map.get(equipamento.get("localizacao_atual_id"), "-")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Origem", value=origem_nome, disabled=True)
        with c2:
            destino_nome = st.selectbox(
                "Destino",
                options=[l["nome"] for l in locais if l["nome"] != origem_nome],
            )

        data_mov = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
        observacao = st.text_area("Observação (opcional)", placeholder="Opcional")

        confirmar = st.form_submit_button("Confirmar movimentação")

        if confirmar:
            destino_id = next(l["id"] for l in locais if l["nome"] == destino_nome)
            # O status "Disponível" não existe mais: todo equipamento
            # movimentado passa a "Em operação", independente do tipo do
            # local de destino.
            novo_status = svc_equip.STATUS_OPERACIONAL

            usuario = usuario_logado()
            svc_mov.mover_equipamento(
                equipamento_id=equipamento["id"],
                origem_id=equipamento.get("localizacao_atual_id"),
                destino_id=destino_id,
                data_movimentacao=data_mov.isoformat(),
                responsavel_id=usuario["id"] if usuario else None,
                observacao=observacao,
                novo_status=novo_status,
            )
            st.success(
                f"{codigo_selecionado} movido de {origem_nome} para {destino_nome}. "
                f"Novo status: {novo_status}."
            )
            st.rerun()

    st.markdown('<div class="section-title">Situação atual dos equipamentos</div>', unsafe_allow_html=True)
    import pandas as pd

    linhas = [
        {
            "Código": esc(e["codigo"]),
            "Localização": esc(locais_map.get(e.get("localizacao_atual_id"), "-")),
            "Status": status_badge(e["status"]),
        }
        for e in equipamentos
    ]
    df = pd.DataFrame(linhas)
    st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)

import pandas as pd
import streamlit as st

from services import equipamentos as svc_equip
from services import movimentacoes as svc_mov
from services import locais as svc_locais
from utils.helpers import formatar_data_br

ICONES_TIPO = {
    "Chegada": "📦",
    "Movimentação": "🔁",
    "Quebra": "⚠️",
    "Substituição": "🔄",
    "Manutenção": "🛠️",
}


def render():
    st.markdown('<div class="page-title">Histórico</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Linha do tempo de cada equipamento</div>',
        unsafe_allow_html=True,
    )

    equipamentos = svc_equip.listar_equipamentos(apenas_ativos=False)
    if not equipamentos:
        st.info("Nenhum equipamento cadastrado ainda.")
        return

    codigos_map = {e["codigo"]: e for e in equipamentos}
    codigo_selecionado = st.selectbox("Selecione um equipamento", options=list(codigos_map.keys()))
    equipamento = codigos_map[codigo_selecionado]

    locais_map = svc_locais.mapa_id_para_nome()
    eventos = svc_mov.historico_equipamento(equipamento["id"])

    st.markdown('<div class="section-title">Linha do tempo</div>', unsafe_allow_html=True)

    if not eventos:
        st.caption("Nenhum evento registrado para este equipamento.")
        return

    for ev in eventos:
        icone = ICONES_TIPO.get(ev["tipo_movimentacao"], "•")
        destino_nome = locais_map.get(ev.get("destino_id"))
        origem_nome = locais_map.get(ev.get("origem_id"))

        descricao = ev["tipo_movimentacao"]
        if ev["tipo_movimentacao"] == "Movimentação" and origem_nome and destino_nome:
            descricao = f"Movimentado de {origem_nome} para {destino_nome}"
        elif ev["tipo_movimentacao"] == "Chegada" and destino_nome:
            descricao = f"Chegada — destinado para {destino_nome}"
        elif ev["tipo_movimentacao"] == "Substituição" and destino_nome:
            descricao = f"Substituição — entrou em operação em {destino_nome}"

        st.markdown(
            f"**{formatar_data_br(ev['data_movimentacao'])}** — {icone} {descricao}"
        )
        if ev.get("observacao"):
            st.caption(ev["observacao"])

    st.markdown("---")
    st.markdown('<div class="section-title">Histórico geral (últimos eventos)</div>', unsafe_allow_html=True)
    geral = svc_mov.historico_geral(limite=100)
    if geral:
        linhas = []
        for ev in geral:
            equip_info = ev.get("equipamentos") or {}
            linhas.append(
                {
                    "Data": formatar_data_br(ev["data_movimentacao"]),
                    "Equipamento": equip_info.get("codigo", "-"),
                    "Evento": ev["tipo_movimentacao"],
                    "Observação": ev.get("observacao") or "-",
                }
            )
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)

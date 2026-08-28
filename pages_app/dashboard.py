import streamlit as st
import pandas as pd

from services import equipamentos as svc_equip
from services import distribuicao as svc_dist
from services import substituicoes as svc_sub
from utils.helpers import propriedade_badge, formatar_data_br, esc


def _kpi(col, label, valor, accent):
    with col:
        st.markdown(
            f"""
            <div class="kpi-card kpi-accent {accent}">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{valor}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render():
    st.markdown('<div class="page-title">Dashboard</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Visão geral da frota de paleteiras</div>',
        unsafe_allow_html=True,
    )

    contagem = svc_equip.contar_por_status()
    substituicoes_pendentes = svc_sub.listar_pendentes()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    _kpi(col1, "Total de Paleteiras", contagem["Total"], "cinza")
    _kpi(col2, "Disponíveis", contagem[svc_equip.STATUS_DISPONIVEL], "azul")
    _kpi(col3, "Em Operação", contagem[svc_equip.STATUS_OPERACIONAL], "verde")
    _kpi(col4, "Em Manutenção", contagem[svc_equip.STATUS_MANUTENCAO], "laranja")
    _kpi(col5, "Quebradas", contagem[svc_equip.STATUS_QUEBRADA], "vermelho")
    _kpi(col6, "Substituições Pendentes", len(substituicoes_pendentes), "roxo")

    # --------------------- DISTRIBUIÇÃO ---------------------
    st.markdown('<div class="section-title">Distribuição por Unidade</div>', unsafe_allow_html=True)

    linhas = svc_dist.visao_distribuicao()
    if linhas:
        df = pd.DataFrame(
            [
                {
                    "Setor": l["unidade"],
                    "Planejado": l["planejado"],
                    "Em Operação": l["em_operacao"],
                    "Quebradas": l["quebradas"],
                    "Déficit": l["deficit"],
                }
                for l in linhas
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma unidade cadastrada ainda.")

    # --------------------- SUBSTITUIÇÕES PENDENTES ---------------------
    st.markdown('<div class="section-title">Substituições Pendentes</div>', unsafe_allow_html=True)

    if substituicoes_pendentes:
        linhas_html = []
        for s in substituicoes_pendentes:
            equip = s.get("equipamentos") or {}
            local = s.get("locais") or {}
            linhas_html.append(
                {
                    "Equipamento": esc(equip.get("codigo")),
                    "Local": esc(local.get("nome")),
                    "Propriedade": propriedade_badge(equip.get("propriedade", "-")),
                    "Motivo": esc(s.get("motivo")),
                    "Status": '<span class="badge badge-roxo">PENDENTE</span>',
                    "Data": formatar_data_br(s.get("data_solicitacao")),
                }
            )
        df_sub = pd.DataFrame(linhas_html)
        st.write(df_sub.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.success("Nenhuma substituição pendente no momento.")

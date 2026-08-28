import pandas as pd
import streamlit as st

from services import distribuicao as svc_dist
from services import locais as svc_locais


def render():
    st.markdown('<div class="page-title">Distribuição</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Comparativo entre distribuição planejada e operacional</div>',
        unsafe_allow_html=True,
    )

    linhas = svc_dist.visao_distribuicao()

    if linhas:
        df = pd.DataFrame(
            [
                {
                    "Unidade": l["unidade"],
                    "Planejado": l["planejado"],
                    "Em Operação": l["em_operacao"],
                    "Quebradas": l["quebradas"],
                    "Déficit": l["deficit"],
                }
                for l in linhas
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)

        total_deficit = sum(l["deficit"] for l in linhas)
        if total_deficit > 0:
            st.warning(f"Déficit total identificado: {total_deficit} equipamento(s).")
        else:
            st.success("Nenhum déficit identificado em nenhuma unidade.")
    else:
        st.info("Nenhuma unidade cadastrada ainda.")

    st.markdown("---")
    st.markdown('<div class="section-title">Definir quantidade planejada por unidade</div>', unsafe_allow_html=True)

    locais = svc_locais.listar_locais()
    if not locais:
        st.info("Cadastre locais para configurar a distribuição planejada.")
        return

    planejado_map = svc_dist.listar_planejado()

    with st.form("form_planejado"):
        local_nome = st.selectbox("Unidade", options=[l["nome"] for l in locais])
        local_id = next(l["id"] for l in locais if l["nome"] == local_nome)
        valor_atual = planejado_map.get(local_id, 0)
        nova_quantidade = st.number_input(
            "Quantidade planejada", min_value=0, max_value=999, value=valor_atual, step=1
        )
        salvar = st.form_submit_button("Salvar")

        if salvar:
            svc_dist.definir_planejado(local_id, int(nova_quantidade))
            st.success(f"Distribuição planejada de {local_nome} atualizada para {int(nova_quantidade)}.")
            st.rerun()

from datetime import date

import pandas as pd
import streamlit as st

from services import equipamentos as svc_equip
from services import substituicoes as svc_sub
from utils.auth import usuario_logado
from utils.helpers import propriedade_badge, formatar_data_br


def render():
    st.markdown('<div class="page-title">Substituições</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Substituições geradas automaticamente por quebra</div>',
        unsafe_allow_html=True,
    )

    pendentes = svc_sub.listar_pendentes()

    if not pendentes:
        st.success("Nenhuma substituição pendente no momento.")
    else:
        st.markdown('<div class="section-title">Pendentes</div>', unsafe_allow_html=True)

        # Não existe mais status "Disponível" — a reserva para substituição
        # agora é todo equipamento operacional parado em CD/Estoque.
        equipamentos_disponiveis = svc_equip.listar_em_estoque()
        mapa_disponiveis = {e["codigo"]: e for e in equipamentos_disponiveis}

        for s in pendentes:
            equip = s.get("equipamentos") or {}
            local = s.get("locais") or {}
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 3])
                with c1:
                    st.markdown(f"**{equip.get('codigo', '-')}**")
                    st.caption(f"Local: {local.get('nome', '-')}")
                with c2:
                    st.markdown(propriedade_badge(equip.get("propriedade", "-")), unsafe_allow_html=True)
                    st.caption(f"Motivo: {s.get('motivo', '-')} · Desde {formatar_data_br(s.get('data_solicitacao'))}")
                with c3:
                    if mapa_disponiveis:
                        with st.form(f"form_sub_{s['id']}"):
                            novo_codigo = st.selectbox(
                                "Novo equipamento",
                                options=list(mapa_disponiveis.keys()),
                                key=f"novo_{s['id']}",
                            )
                            data_atendimento = st.date_input(
                                "Data", value=date.today(), format="DD/MM/YYYY", key=f"data_{s['id']}"
                            )
                            confirmar = st.form_submit_button("Confirmar substituição")

                            if confirmar:
                                usuario = usuario_logado()
                                substituto = mapa_disponiveis[novo_codigo]
                                svc_sub.confirmar_substituicao(
                                    substituicao_id=s["id"],
                                    equipamento_substituido_id=s["equipamento_substituido_id"],
                                    equipamento_substituto_id=substituto["id"],
                                    local_id=s["local_id"],
                                    data_atendimento=data_atendimento.isoformat(),
                                    responsavel_id=usuario["id"] if usuario else None,
                                )
                                st.success(
                                    f"{novo_codigo} agora está em operação em {local.get('nome', '-')}."
                                )
                                st.rerun()
                    else:
                        st.warning("Não há equipamentos disponíveis para substituição no momento.")

    st.markdown('<div class="section-title">Histórico de substituições</div>', unsafe_allow_html=True)
    todas = svc_sub.listar_todas()
    if todas:
        linhas = []
        for s in todas:
            equip = s.get("equipamentos") or {}
            local = s.get("locais") or {}
            linhas.append(
                {
                    "Equipamento substituído": equip.get("codigo", "-"),
                    "Local": local.get("nome", "-"),
                    "Status": s.get("status"),
                    "Solicitado em": formatar_data_br(s.get("data_solicitacao")),
                    "Atendido em": formatar_data_br(s.get("data_atendimento")),
                }
            )
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    else:
        st.caption("Nenhum registro de substituição ainda.")

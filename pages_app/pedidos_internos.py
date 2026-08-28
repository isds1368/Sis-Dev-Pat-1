import pandas as pd
import streamlit as st

from services import pedidos_internos as svc_pi
from utils.auth import usuario_logado
from utils.helpers import esc, formatar_data_br, dias_uteis_entre, parse_date
from datetime import date


@st.dialog("Detalhes do Pedido Interno")
def _popup_detalhes(pedido: dict):
    st.markdown(f"### {pedido['numero_interno']}")

    atrasado = svc_pi.esta_atrasado(pedido)
    if pedido["status"] == "Aberto":
        cor = "vermelho" if atrasado else "azul"
        texto_status = "Em atraso" if atrasado else "No prazo"
    elif pedido["status"] == "Atendido":
        cor = "verde"
        texto_status = "Atendido"
    else:
        cor = "cinza"
        texto_status = pedido["status"]
    st.markdown(f'<span class="badge badge-{cor}">{texto_status}</span>', unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Solicitação junto ao fornecedor")
        st.markdown(f"**{esc(pedido['numero_solicitacao_fornecedor'])}**")
        st.caption("Data de abertura")
        st.markdown(f"**{formatar_data_br(pedido['data_abertura'])}**")
    with c2:
        st.caption("SLA previsto")
        st.markdown(f"**{pedido['dias_uteis_sla']} dia(s) útil(eis) — até {formatar_data_br(pedido['data_prevista'])}**")
        if pedido["status"] == "Atendido":
            st.caption("Data de atendimento")
            st.markdown(f"**{formatar_data_br(pedido['data_atendimento'])}**")

    if pedido.get("nota_sla") is not None:
        st.caption("Nota de SLA")
        st.markdown(f"**{pedido['nota_sla']} / 100**")

    st.markdown("---")
    st.markdown("**Equipamentos deste pedido**")

    itens = svc_pi.itens_do_pedido(pedido["id"], apenas_pendentes=False)
    if itens:
        linhas = []
        for item in itens:
            equip = item.get("equipamentos") or {}
            local = item.get("locais") or {}
            linhas.append(
                {
                    "Equipamento": equip.get("codigo", "-"),
                    "Setor": local.get("nome", "-"),
                    "Status": item.get("status"),
                }
            )
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    else:
        st.caption("Nenhum equipamento vinculado.")


def _card_pedido(pedido: dict):
    atrasado = svc_pi.esta_atrasado(pedido)
    cor_accent = "vermelho" if atrasado else "azul"
    itens = svc_pi.itens_do_pedido(pedido["id"], apenas_pendentes=True)

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="kpi-card kpi-accent {cor_accent}" style="padding:0.8rem 1rem;">
                <div class="kpi-label">{esc(pedido['numero_interno'])}</div>
                <div style="font-size:0.85rem; color:var(--cor-texto-suave); margin-bottom:0.3rem;">
                    Aberto em {formatar_data_br(pedido['data_abertura'])}
                </div>
                <div style="font-size:0.85rem;">
                    SLA: <strong>{pedido['dias_uteis_sla']} dia(s) útil(eis)</strong><br/>
                    Previsto: <strong>{formatar_data_br(pedido['data_prevista'])}</strong>
                </div>
                <div style="margin-top:0.4rem;">
                    {'<span class="badge badge-vermelho">Em atraso</span>' if atrasado else '<span class="badge badge-azul">No prazo</span>'}
                    <span class="badge badge-cinza">{len(itens)} pendente(s)</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Ver detalhes", key=f"detalhes_{pedido['id']}", use_container_width=True):
            _popup_detalhes(pedido)


def render():
    st.markdown('<div class="page-title">Pedidos Internos</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Chamados abertos junto ao fornecedor para substituição de equipamentos</div>',
        unsafe_allow_html=True,
    )

    abertos = svc_pi.listar_abertos()

    st.markdown('<div class="section-title">Em aberto</div>', unsafe_allow_html=True)
    if abertos:
        colunas = st.columns(3)
        for i, pedido in enumerate(abertos):
            with colunas[i % 3]:
                _card_pedido(pedido)
    else:
        st.success("Nenhum pedido interno em aberto no momento.")

    # ---------------- Abrir novo pedido ----------------
    st.markdown("---")
    st.markdown('<div class="section-title">Abrir novo pedido interno</div>', unsafe_allow_html=True)

    candidatos = svc_pi.equipamentos_quebrados_disponiveis_para_pedido()
    if not candidatos:
        st.info(
            "Não há equipamentos quebrados disponíveis para vincular a um novo pedido "
            "(todos já estão em algum chamado aberto, ou não há quebras registradas)."
        )
    else:
        mapa_codigos = {e["codigo"]: e["id"] for e in candidatos}
        with st.form("form_novo_pedido"):
            c1, c2 = st.columns(2)
            with c1:
                numero_fornecedor = st.text_input(
                    "Número da solicitação junto ao fornecedor", max_chars=60
                )
            with c2:
                dias_uteis = st.number_input(
                    "Dias úteis para atendimento (SLA)", min_value=1, max_value=90, value=5, step=1
                )

            codigos_selecionados = st.multiselect(
                "Equipamentos que serão substituídos", options=list(mapa_codigos.keys())
            )

            abrir = st.form_submit_button("Abrir pedido interno")

            if abrir:
                if not numero_fornecedor.strip():
                    st.error("Informe o número da solicitação junto ao fornecedor.")
                elif not codigos_selecionados:
                    st.error("Selecione ao menos um equipamento.")
                else:
                    usuario = usuario_logado()
                    equipamento_ids = [mapa_codigos[c] for c in codigos_selecionados]
                    pedido = svc_pi.abrir_pedido(
                        numero_solicitacao_fornecedor=numero_fornecedor.strip(),
                        dias_uteis_sla=int(dias_uteis),
                        equipamento_ids=equipamento_ids,
                        responsavel_id=usuario["id"] if usuario else None,
                    )
                    st.success(
                        f"Pedido {pedido['numero_interno']} aberto. "
                        f"Prazo: {formatar_data_br(pedido['data_prevista'])}."
                    )
                    st.rerun()

    # ---------------- Histórico ----------------
    st.markdown("---")
    st.markdown('<div class="section-title">Histórico de pedidos concluídos</div>', unsafe_allow_html=True)

    historico = svc_pi.listar_historico()
    if historico:
        linhas = []
        for p in historico:
            dias_atraso = dias_uteis_entre(parse_date(p["data_prevista"]), parse_date(p.get("data_atendimento")))
            linhas.append(
                {
                    "Pedido": p["numero_interno"],
                    "Solicitação fornecedor": p["numero_solicitacao_fornecedor"],
                    "Abertura": formatar_data_br(p["data_abertura"]),
                    "Previsto": formatar_data_br(p["data_prevista"]),
                    "Atendido": formatar_data_br(p.get("data_atendimento")),
                    "Dias de atraso": dias_atraso,
                    "Nota SLA": p.get("nota_sla"),
                    "Status": p["status"],
                }
            )
        st.dataframe(pd.DataFrame(linhas), hide_index=True, use_container_width=True)
    else:
        st.caption("Nenhum pedido concluído ainda.")

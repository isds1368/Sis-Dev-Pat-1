from datetime import date

import streamlit as st

from services import equipamentos as svc_equip
from services import locais as svc_locais
from services import movimentacoes as svc_mov
from services import pedidos_internos as svc_pi
from utils.auth import usuario_logado
from utils.helpers import esc

OPCAO_SEM_VINCULO = "Nenhum (chegada sem vínculo a pedido interno)"
OPCAO_PLACEHOLDER = "— Selecione uma opção —"


def _etapa_reconhecimento_pedido():
    """
    Passo 0: antes de qualquer campo de chegada, o sistema reconhece se
    existe um chamado interno em aberto relacionado a esta entrega.
    Nada do restante do formulário aparece até uma escolha ser feita aqui.
    """
    st.markdown('<div class="section-title">Chamado interno relacionado</div>', unsafe_allow_html=True)
    st.caption("Selecione o pedido interno que esta chegada está atendendo, se houver.")

    abertos = svc_pi.listar_abertos()
    mapa_pedidos = {p["numero_interno"]: p for p in abertos}
    opcoes = [OPCAO_PLACEHOLDER, OPCAO_SEM_VINCULO] + list(mapa_pedidos.keys())

    escolha = st.selectbox("Pedido interno", options=opcoes, key="chegada_escolha_pedido")

    if escolha == OPCAO_PLACEHOLDER:
        st.session_state.pop("chegada_pedido_id", None)
        return None

    if escolha == OPCAO_SEM_VINCULO:
        st.session_state["chegada_pedido_id"] = None
        st.info("Esta chegada não será vinculada a nenhum pedido interno.")
        return "confirmado"

    pedido = mapa_pedidos[escolha]
    st.session_state["chegada_pedido_id"] = pedido["id"]

    itens = svc_pi.itens_do_pedido(pedido["id"], apenas_pendentes=True)
    codigos = [esc((item.get("equipamentos") or {}).get("codigo", "-")) for item in itens]
    setores = svc_pi.pendentes_por_setor(pedido["id"])

    st.markdown(
        f"""
        <div class="kpi-card kpi-accent azul" style="margin-top:0.5rem;">
            <div class="kpi-label">Chamado reconhecido</div>
            <div class="kpi-value" style="font-size:1.3rem;">{esc(pedido['numero_interno'])}</div>
            <div style="font-size:0.85rem; margin-top:0.4rem;">
                Nº do chamado no fornecedor: <strong>{esc(pedido['numero_solicitacao_fornecedor'])}</strong><br/>
                Equipamentos a substituir: <strong>{', '.join(codigos) if codigos else '-'}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if setores:
        st.markdown("**Equipamentos quebrados pendentes por setor:**")
        cols = st.columns(len(setores))
        for col, (nome_setor, qtd) in zip(cols, setores.items()):
            with col:
                st.markdown(
                    f'<div class="kpi-card"><div class="kpi-label">{esc(nome_setor)}</div>'
                    f'<div class="kpi-value">{qtd}</div></div>',
                    unsafe_allow_html=True,
                )
    return "confirmado"


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

    # --------- ETAPA 0: reconhecimento do chamado interno ---------
    status_etapa0 = _etapa_reconhecimento_pedido()
    if status_etapa0 is None:
        st.info("Selecione uma opção acima para continuar.")
        return  # as funções abaixo só são ativadas depois da escolha

    pedido_id = st.session_state.get("chegada_pedido_id")
    setores_pendentes_base = svc_pi.pendentes_por_setor(pedido_id) if pedido_id else {}

    st.markdown("---")

    # --------- ETAPA 1: dados gerais da chegada ---------
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
                "pedido_id": pedido_id,
            }
            for chave in list(st.session_state.keys()):
                if chave.startswith("codigo_") or chave.startswith("destino_"):
                    del st.session_state[chave]

    config = st.session_state.get("chegada_config")
    if not config:
        return

    st.markdown("---")
    st.markdown('<div class="section-title">Definir código e destino de cada equipamento</div>', unsafe_allow_html=True)
    st.caption("Cada equipamento pode ter um destino diferente — a decisão é sempre manual.")

    sugestao_base = svc_equip.proximo_codigo_sugerido()
    sugestao_num = int(sugestao_base.split("-")[1])

    # Fora de st.form de propósito: precisa recalcular ao vivo o saldo de
    # pendências por setor conforme os destinos vão sendo escolhidos.
    destinos_escolhidos = []
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
        destinos_escolhidos.append((codigo, destino_nome))

    if config.get("pedido_id") and setores_pendentes_base:
        saldo = dict(setores_pendentes_base)
        for _, destino_nome in destinos_escolhidos:
            if destino_nome in saldo and saldo[destino_nome] > 0:
                saldo[destino_nome] -= 1

        st.markdown("**Saldo de pendências por setor (atualizado conforme você escolhe os destinos):**")
        cols = st.columns(len(saldo))
        for col, (nome_setor, qtd) in zip(cols, saldo.items()):
            with col:
                cor = "verde" if qtd == 0 else "laranja"
                st.markdown(
                    f'<div class="kpi-card kpi-accent {cor}"><div class="kpi-label">{esc(nome_setor)}</div>'
                    f'<div class="kpi-value">{qtd}</div></div>',
                    unsafe_allow_html=True,
                )

    confirmar = st.button("Salvar chegada", type="primary")

    if confirmar:
        codigos_informados = [c.strip() for c, _ in destinos_escolhidos]

        invalidos = [c for c in codigos_informados if not svc_equip.codigo_valido(c)]
        if invalidos:
            st.error(
                f"Códigos inválidos: {', '.join(invalidos)}. "
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
        for codigo, destino_nome in destinos_escolhidos:
            destino_id = nomes_locais[destino_nome]

            # O status "Disponível" não existe mais: todo equipamento entra
            # como "Em operação", esteja o destino sendo uma loja ou um
            # CD/Estoque (parado, aguardando ser usado como substituto).
            status_destino = svc_equip.STATUS_OPERACIONAL

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

            # O chamado só é considerado atendido quando, na própria chegada,
            # a substituição é registrada — é isso que a linha abaixo faz.
            vinculado = False
            if config.get("pedido_id"):
                vinculado = svc_pi.registrar_substituicao_via_chegada(
                    pedido_id=config["pedido_id"],
                    local_id=destino_id,
                    equipamento_substituto_id=equipamento["id"],
                    data_atendimento=config["data_chegada"],
                    responsavel_id=responsavel_id,
                )

            criados.append((codigo, destino_nome, status_destino, vinculado))

        st.success(f"{len(criados)} equipamento(s) registrado(s) com sucesso.")
        for codigo, destino_nome, status_destino, vinculado in criados:
            extra = " · substituição registrada no pedido interno" if vinculado else ""
            st.write(f"- **{codigo}** → {destino_nome} ({status_destino}){extra}")

        pedido_id_usado = config.get("pedido_id")
        if pedido_id_usado:
            pedido_atualizado = svc_pi.obter_pedido(pedido_id_usado)
            if pedido_atualizado and pedido_atualizado["status"] == "Atendido":
                st.balloons()
                st.success(
                    f"Pedido {pedido_atualizado['numero_interno']} totalmente atendido! "
                    f"Nota de SLA: {pedido_atualizado['nota_sla']} / 100."
                )

        st.session_state.pop("chegada_config", None)
        for chave in list(st.session_state.keys()):
            if chave.startswith("codigo_") or chave.startswith("destino_"):
                del st.session_state[chave]

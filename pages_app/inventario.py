import streamlit as st
import pandas as pd

from services import equipamentos as svc_equip
from services import locais as svc_locais
from utils.auth import usuario_logado
from utils.helpers import status_badge, propriedade_badge, formatar_data_br, tempo_de_uso, esc

STATUS_OPCOES = [
    "Todos",
    "Em operação",
    "Em manutenção",
    "Quebrada",
    "Aguardando substituição",
    "Substituído",
]


def render():
    st.markdown('<div class="page-title">Inventário</div>', unsafe_allow_html=True)

    usuario = usuario_logado()
    eh_supervisor = usuario and usuario.get("perfil") == "Supervisor"
    locais_map = svc_locais.mapa_id_para_nome()

    if eh_supervisor:
        nome_local = locais_map.get(usuario.get("local_id"), "seu local")
        st.markdown(
            f'<div class="page-subtitle">Equipamentos do local: <strong>{esc(nome_local)}</strong></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="page-subtitle">Todos os equipamentos cadastrados</div>',
            unsafe_allow_html=True,
        )

    # 'Substituído' fica inativo (ativo=false), então precisa entrar
    # explicitamente com apenas_ativos=False para continuar visível aqui.
    equipamentos = svc_equip.listar_equipamentos(apenas_ativos=False)

    if eh_supervisor:
        equipamentos = [e for e in equipamentos if e.get("localizacao_atual_id") == usuario.get("local_id")]

    if not equipamentos:
        st.info("Nenhum equipamento cadastrado ainda.")
        return

    # ---------------- FILTROS ----------------
    if eh_supervisor:
        c1, c2, c3, c5 = st.columns([2, 1, 1, 1])
    else:
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])

    with c1:
        busca = st.text_input("Pesquisar equipamento...", placeholder="Ex: PAL-001")
    with c2:
        status_filtro = st.selectbox("Status", STATUS_OPCOES)
    with c3:
        propriedade_filtro = st.selectbox("Propriedade", ["Todas", "Própria", "Alugada"])
    if not eh_supervisor:
        with c4:
            local_filtro = st.selectbox("Localização", ["Todas"] + sorted(locais_map.values()))
    else:
        local_filtro = "Todas"
    with c5:
        tipo_filtro = st.selectbox("Tipo", ["Todos"] + svc_equip.TIPOS_EQUIPAMENTO)

    linhas = []
    for e in equipamentos:
        local_nome = locais_map.get(e.get("localizacao_atual_id"), "-")

        if busca and busca.strip().lower() not in e["codigo"].lower():
            continue
        if status_filtro != "Todos" and e["status"] != status_filtro:
            continue
        if propriedade_filtro != "Todas" and e["propriedade"] != propriedade_filtro:
            continue
        if local_filtro != "Todas" and local_nome != local_filtro:
            continue
        if tipo_filtro != "Todos" and e["tipo"] != tipo_filtro:
            continue

        linhas.append(
            {
                # Campos livres (código, fornecedor, local) são escapados:
                # nunca confiar em texto vindo do banco/usuário ao montar HTML.
                "Código": esc(e["codigo"]),
                "Tipo": esc(e["tipo"]),
                "Propriedade": propriedade_badge(e["propriedade"]),
                "Fornecedor": esc(e.get("fornecedor")),
                "Localização": esc(local_nome),
                "Status": status_badge(e["status"]),
                "Data de chegada": formatar_data_br(e["data_chegada"]),
                "Tempo de uso": tempo_de_uso(e["data_chegada"]),
            }
        )

    st.markdown(f'<div class="section-title">{len(linhas)} equipamento(s)</div>', unsafe_allow_html=True)

    if linhas:
        df = pd.DataFrame(linhas)
        st.write(df.to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        st.warning("Nenhum equipamento encontrado com os filtros selecionados.")

"""
Pedidos Internos — chamados abertos junto ao fornecedor para substituição
de equipamentos quebrados. Cada pedido carrega um SLA em dias úteis e,
quando totalmente atendido, recebe uma nota calculada com pesos.

------------------------------------------------------------------
FÓRMULA DA NOTA DE SLA (documentada de propósito — é regra de negócio)
------------------------------------------------------------------
Se atendido dentro do prazo: nota = 100.

Se atendido com atraso:
    penalidade = dias_uteis_de_atraso × PESO_ATRASO_POR_DIA × multiplicador_quantidade
    multiplicador_quantidade = 1 + (quantidade_de_equipamentos - 1) × PESO_EXTRA_POR_EQUIPAMENTO
    nota = max(0, 100 − penalidade)

Ou seja, dois pesos entram na conta:
  1) PESO_ATRASO_POR_DIA — quanto cada dia útil de atraso pesa isoladamente.
  2) PESO_EXTRA_POR_EQUIPAMENTO — pedidos maiores (mais paleteiras
     paradas) são penalizados proporcionalmente mais por dia de atraso,
     porque o impacto operacional de um pedido de 10 equipamentos
     atrasado é maior do que o de 1 equipamento atrasado.
"""
from datetime import date

from utils.database import supabase
from utils.helpers import somar_dias_uteis, dias_uteis_entre, parse_date
from services import equipamentos as svc_equip
from services import substituicoes as svc_sub

PESO_ATRASO_POR_DIA = 8.0
PESO_EXTRA_POR_EQUIPAMENTO = 0.15


def calcular_nota_sla(dias_atraso: int, quantidade_equipamentos: int) -> float:
    if dias_atraso <= 0:
        return 100.0
    multiplicador = 1 + max(0, quantidade_equipamentos - 1) * PESO_EXTRA_POR_EQUIPAMENTO
    penalidade = dias_atraso * PESO_ATRASO_POR_DIA * multiplicador
    return round(max(0.0, 100.0 - penalidade), 1)


# ------------------------------------------------------------
# Criação
# ------------------------------------------------------------
def _proximo_numero_interno() -> str:
    resp = supabase().table("pedidos_internos").select("numero_interno").execute()
    maior = 0
    for p in resp.data:
        numero = p.get("numero_interno", "")
        if numero.startswith("PI-"):
            try:
                maior = max(maior, int(numero.split("-")[1]))
            except (IndexError, ValueError):
                continue
    return f"PI-{maior + 1:04d}"


def equipamentos_quebrados_disponiveis_para_pedido() -> list[dict]:
    """
    Equipamentos com status Quebrada. Uma vez vinculados a um pedido, o
    status muda para 'Aguardando substituição' e eles somem naturalmente
    desta lista — não é mais preciso checar vínculo, o status já resolve.
    """
    return [e for e in svc_equip.listar_equipamentos() if e["status"] == svc_equip.STATUS_QUEBRADA]


def abrir_pedido(
    numero_solicitacao_fornecedor: str,
    dias_uteis_sla: int,
    equipamento_ids: list[str],
    responsavel_id: str | None = None,
) -> dict:
    if not equipamento_ids:
        raise ValueError("Selecione ao menos um equipamento a ser substituído.")
    if dias_uteis_sla <= 0:
        raise ValueError("O prazo em dias úteis deve ser maior que zero.")

    numero_interno = _proximo_numero_interno()
    data_abertura = date.today()
    data_prevista = somar_dias_uteis(data_abertura, dias_uteis_sla)

    resp = (
        supabase()
        .table("pedidos_internos")
        .insert(
            {
                "numero_interno": numero_interno,
                "numero_solicitacao_fornecedor": numero_solicitacao_fornecedor,
                "dias_uteis_sla": int(dias_uteis_sla),
                "data_abertura": data_abertura.isoformat(),
                "data_prevista": data_prevista.isoformat(),
                "status": "Aberto",
                "responsavel_abertura_id": responsavel_id,
            }
        )
        .execute()
    )
    pedido = resp.data[0]

    for equipamento_id in equipamento_ids:
        _vincular_equipamento(pedido["id"], equipamento_id)

    return pedido


def _vincular_equipamento(pedido_id: str, equipamento_id: str):
    equip = svc_equip.obter_equipamento(equipamento_id)

    existente = (
        supabase()
        .table("substituicoes")
        .select("id")
        .eq("equipamento_substituido_id", equipamento_id)
        .eq("status", "Pendente")
        .is_("pedido_interno_id", "null")
        .limit(1)
        .execute()
    )
    if existente.data:
        supabase().table("substituicoes").update({"pedido_interno_id": pedido_id}).eq(
            "id", existente.data[0]["id"]
        ).execute()
    else:
        supabase().table("substituicoes").insert(
            {
                "equipamento_substituido_id": equipamento_id,
                "local_id": equip.get("localizacao_atual_id") if equip else None,
                "motivo": "Quebra",
                "data_solicitacao": date.today().isoformat(),
                "status": "Pendente",
                "pedido_interno_id": pedido_id,
            }
        ).execute()

    # Ao entrar em um pedido de substituição, o equipamento sai de
    # "Quebrada" e passa a "Aguardando substituição" — deixa de aparecer
    # como candidato para um novo pedido e fica visualmente distinto no
    # Inventário/Dashboard enquanto o fornecedor não atende o chamado.
    svc_equip.atualizar_status_localizacao(
        equipamento_id, status=svc_equip.STATUS_AGUARDANDO_SUBSTITUICAO
    )


# ------------------------------------------------------------
# Consultas
# ------------------------------------------------------------
def listar_abertos() -> list[dict]:
    resp = (
        supabase()
        .table("pedidos_internos")
        .select("*")
        .eq("status", "Aberto")
        .order("data_abertura")
        .execute()
    )
    return resp.data


def listar_historico(limite: int = 200) -> list[dict]:
    resp = (
        supabase()
        .table("pedidos_internos")
        .select("*")
        .neq("status", "Aberto")
        .order("data_atendimento", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data


def obter_pedido(pedido_id: str) -> dict | None:
    resp = supabase().table("pedidos_internos").select("*").eq("id", pedido_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def itens_do_pedido(pedido_id: str, apenas_pendentes: bool = True) -> list[dict]:
    q = (
        supabase()
        .table("substituicoes")
        .select(
            "*, equipamentos!substituicoes_equipamento_substituido_id_fkey(codigo), locais(nome)"
        )
        .eq("pedido_interno_id", pedido_id)
    )
    if apenas_pendentes:
        q = q.eq("status", "Pendente")
    return q.execute().data


def pendentes_por_setor(pedido_id: str) -> dict:
    """{nome_do_local: quantidade_pendente} — usado na tela de Chegada."""
    itens = itens_do_pedido(pedido_id, apenas_pendentes=True)
    contagem = {}
    for item in itens:
        nome_local = (item.get("locais") or {}).get("nome", "-")
        contagem[nome_local] = contagem.get(nome_local, 0) + 1
    return contagem


def esta_atrasado(pedido: dict) -> bool:
    if pedido["status"] != "Aberto":
        return False
    return date.today() > parse_date(pedido["data_prevista"])


# ------------------------------------------------------------
# Atendimento (só acontece através da Chegada)
# ------------------------------------------------------------
def registrar_substituicao_via_chegada(
    pedido_id: str,
    local_id: str,
    equipamento_substituto_id: str,
    data_atendimento: str,
    responsavel_id: str | None = None,
) -> bool:
    """
    Vincula automaticamente o equipamento recém-chegado à pendência mais
    antiga daquele setor, dentro deste pedido interno. Retorna False se não
    havia pendência daquele setor neste pedido (chegada segue normalmente).
    """
    pendentes = (
        supabase()
        .table("substituicoes")
        .select("*")
        .eq("pedido_interno_id", pedido_id)
        .eq("local_id", local_id)
        .eq("status", "Pendente")
        .order("data_solicitacao")
        .limit(1)
        .execute()
        .data
    )
    if not pendentes:
        return False

    item = pendentes[0]
    svc_sub.confirmar_substituicao(
        substituicao_id=item["id"],
        equipamento_substituido_id=item["equipamento_substituido_id"],
        equipamento_substituto_id=equipamento_substituto_id,
        local_id=local_id,
        data_atendimento=data_atendimento,
        responsavel_id=responsavel_id,
    )

    _verificar_conclusao(pedido_id, data_atendimento, responsavel_id)
    return True


def _verificar_conclusao(pedido_id: str, data_atendimento_str: str, responsavel_id: str | None):
    ainda_pendente = itens_do_pedido(pedido_id, apenas_pendentes=True)
    if ainda_pendente:
        return  # pedido só é concluído quando TODOS os itens foram substituídos

    pedido = obter_pedido(pedido_id)
    data_prevista = parse_date(pedido["data_prevista"])
    data_atendimento = parse_date(data_atendimento_str)
    dias_atraso = dias_uteis_entre(data_prevista, data_atendimento)

    total = (
        supabase()
        .table("substituicoes")
        .select("id")
        .eq("pedido_interno_id", pedido_id)
        .execute()
        .data
    )
    quantidade = len(total) or 1

    nota = calcular_nota_sla(dias_atraso, quantidade)

    supabase().table("pedidos_internos").update(
        {
            "status": "Atendido",
            "data_atendimento": data_atendimento_str,
            "nota_sla": nota,
            "responsavel_atendimento_id": responsavel_id,
        }
    ).eq("id", pedido_id).execute()

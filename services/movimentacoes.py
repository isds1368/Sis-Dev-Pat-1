from utils.database import supabase
from services import equipamentos as svc_equip


def registrar_movimentacao(
    equipamento_id: str,
    tipo_movimentacao: str,
    data_movimentacao: str,
    origem_id: str | None = None,
    destino_id: str | None = None,
    responsavel_id: str | None = None,
    observacao: str | None = None,
) -> dict:
    resp = (
        supabase()
        .table("movimentacoes")
        .insert(
            {
                "equipamento_id": equipamento_id,
                "tipo_movimentacao": tipo_movimentacao,
                "origem_id": origem_id,
                "destino_id": destino_id,
                "data_movimentacao": data_movimentacao,
                "responsavel_id": responsavel_id,
                "observacao": observacao,
            }
        )
        .execute()
    )
    return resp.data[0] if resp.data else None


def registrar_chegada(
    codigo: str,
    tipo: str,
    propriedade: str,
    fornecedor: str,
    data_chegada: str,
    destino_id: str,
    status_destino: str,
    responsavel_id: str | None = None,
) -> dict:
    """
    Cria o equipamento já com o destino definido pelo usuário e grava
    duas entradas de histórico: Chegada + destinação inicial.
    """
    equipamento = svc_equip.criar_equipamento(
        codigo=codigo,
        tipo=tipo,
        propriedade=propriedade,
        fornecedor=fornecedor,
        data_chegada=data_chegada,
        localizacao_atual_id=destino_id,
        status=status_destino,
    )

    registrar_movimentacao(
        equipamento_id=equipamento["id"],
        tipo_movimentacao="Chegada",
        data_movimentacao=data_chegada,
        origem_id=None,
        destino_id=destino_id,
        responsavel_id=responsavel_id,
        observacao=f"Chegada registrada. Fornecedor: {fornecedor or '-'}",
    )
    return equipamento


def mover_equipamento(
    equipamento_id: str,
    origem_id: str | None,
    destino_id: str,
    data_movimentacao: str,
    responsavel_id: str | None = None,
    observacao: str | None = None,
    novo_status: str = svc_equip.STATUS_OPERACIONAL,
):
    """Move um equipamento, atualiza sua localização/status e grava histórico."""
    registrar_movimentacao(
        equipamento_id=equipamento_id,
        tipo_movimentacao="Movimentação",
        data_movimentacao=data_movimentacao,
        origem_id=origem_id,
        destino_id=destino_id,
        responsavel_id=responsavel_id,
        observacao=observacao,
    )
    svc_equip.atualizar_status_localizacao(
        equipamento_id, status=novo_status, localizacao_atual_id=destino_id
    )


def historico_equipamento(equipamento_id: str) -> list[dict]:
    resp = (
        supabase()
        .table("movimentacoes")
        .select("*")
        .eq("equipamento_id", equipamento_id)
        .order("data_movimentacao")
        .order("created_at")
        .execute()
    )
    return resp.data


def historico_geral(limite: int = 200) -> list[dict]:
    resp = (
        supabase()
        .table("movimentacoes")
        .select("*, equipamentos(codigo)")
        .order("created_at", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data

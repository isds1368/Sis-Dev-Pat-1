from utils.database import supabase
from services import equipamentos as svc_equip
from services import movimentacoes as svc_mov


def listar_pendentes() -> list[dict]:
    resp = (
        supabase()
        .table("substituicoes")
        .select("*, equipamentos!substituicoes_equipamento_substituido_id_fkey(codigo, propriedade), locais(nome)")
        .eq("status", "Pendente")
        .order("data_solicitacao")
        .execute()
    )
    return resp.data


def listar_todas(limite: int = 200) -> list[dict]:
    resp = (
        supabase()
        .table("substituicoes")
        .select("*, equipamentos!substituicoes_equipamento_substituido_id_fkey(codigo, propriedade), locais(nome)")
        .order("data_solicitacao", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data


def confirmar_substituicao(
    substituicao_id: str,
    equipamento_substituido_id: str,
    equipamento_substituto_id: str,
    local_id: str,
    data_atendimento: str,
    observacao: str | None = None,
    responsavel_id: str | None = None,
):
    """
    1) Equipamento antigo permanece no histórico como Quebrada (não é reativado).
    2) Equipamento substituto passa a Em operação no local.
    3) Substituição é marcada como Concluída.
    4) Déficit do local é recalculado automaticamente na próxima leitura da distribuição.
    """
    svc_equip.atualizar_status_localizacao(
        equipamento_substituto_id,
        status=svc_equip.STATUS_OPERACIONAL,
        localizacao_atual_id=local_id,
    )

    svc_mov.registrar_movimentacao(
        equipamento_id=equipamento_substituto_id,
        tipo_movimentacao="Substituição",
        data_movimentacao=data_atendimento,
        origem_id=None,
        destino_id=local_id,
        responsavel_id=responsavel_id,
        observacao=f"Substitui o equipamento em ocorrência de quebra. {observacao or ''}".strip(),
    )

    supabase().table("substituicoes").update(
        {
            "equipamento_substituto_id": equipamento_substituto_id,
            "data_atendimento": data_atendimento,
            "status": "Concluída",
            "observacao": observacao,
        }
    ).eq("id", substituicao_id).execute()

from utils.database import supabase
from services import equipamentos as svc_equip
from services import movimentacoes as svc_mov


def listar_pendentes(apenas_sem_pedido_interno: bool = True) -> list[dict]:
    """
    Por padrão, mostra apenas pendências AVULSAS (não vinculadas a nenhum
    Pedido Interno), pois as vinculadas já aparecem como itens dos cards
    em 'Pedidos Internos' — evita mostrar a mesma pendência duas vezes.
    """
    q = (
        supabase()
        .table("substituicoes")
        .select("*, equipamentos!substituicoes_equipamento_substituido_id_fkey(codigo, propriedade), locais(nome)")
        .eq("status", "Pendente")
    )
    if apenas_sem_pedido_interno:
        q = q.is_("pedido_interno_id", "null")
    return q.order("data_solicitacao").execute().data


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
    1) Equipamento antigo passa a 'Substituído' e é desativado — nunca mais
       conta como disponível, em nenhuma hipótese, a não ser que uma nova
       entrada seja registrada com o mesmo código. Permanece no histórico.
    2) Equipamento substituto passa a Em operação no local.
    3) Substituição é marcada como Concluída.
    4) Déficit do local é recalculado automaticamente na próxima leitura da distribuição.
    """
    svc_equip.retirar_equipamento(equipamento_substituido_id)

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

from utils.database import supabase
from utils.helpers import calcular_deficit
from services import locais as svc_locais
from services import equipamentos as svc_equip


def listar_planejado() -> dict:
    """Retorna {local_id: quantidade_planejada}"""
    resp = supabase().table("distribuicao_planejada").select("*").eq("ativo", True).execute()
    return {d["local_id"]: d["quantidade_planejada"] for d in resp.data}


def definir_planejado(local_id: str, quantidade: int):
    existente = (
        supabase()
        .table("distribuicao_planejada")
        .select("*")
        .eq("local_id", local_id)
        .limit(1)
        .execute()
    )
    if existente.data:
        supabase().table("distribuicao_planejada").update(
            {"quantidade_planejada": quantidade}
        ).eq("local_id", local_id).execute()
    else:
        supabase().table("distribuicao_planejada").insert(
            {"local_id": local_id, "quantidade_planejada": quantidade}
        ).execute()


def visao_distribuicao() -> list[dict]:
    """
    Monta a tabela: UNIDADE | PLANEJADO | EM OPERAÇÃO | QUEBRADAS | DÉFICIT
    Regra: quebrado nunca conta como operacional.
    """
    locais = svc_locais.listar_locais()
    planejado_map = listar_planejado()
    equipamentos = svc_equip.listar_equipamentos()

    linhas = []
    for local in locais:
        local_id = local["id"]
        eq_no_local = [e for e in equipamentos if e.get("localizacao_atual_id") == local_id]

        em_operacao = sum(1 for e in eq_no_local if e["status"] == svc_equip.STATUS_OPERACIONAL)
        # "Quebradas" agrupa Quebrada + Aguardando substituição: ambos são
        # equipamentos fora de operação por causa de uma quebra, só que em
        # etapas diferentes do processo de reposição junto ao fornecedor.
        quebradas = sum(
            1 for e in eq_no_local
            if e["status"] in (svc_equip.STATUS_QUEBRADA, svc_equip.STATUS_AGUARDANDO_SUBSTITUICAO)
        )
        planejado = planejado_map.get(local_id, 0)

        linhas.append(
            {
                "local_id": local_id,
                "unidade": local["nome"],
                "planejado": planejado,
                "em_operacao": em_operacao,
                "quebradas": quebradas,
                "deficit": calcular_deficit(planejado, em_operacao),
            }
        )
    return linhas


def deficit_do_local(local_id: str) -> int:
    for linha in visao_distribuicao():
        if linha["local_id"] == local_id:
            return linha["deficit"]
    return 0

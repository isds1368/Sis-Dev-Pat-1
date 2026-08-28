from utils.database import supabase
from services import equipamentos as svc_equip
from services import movimentacoes as svc_mov
from services import distribuicao as svc_dist

# Os motivos de quebra agora são cadastrados/editados em
# Configurações → Cadastros (tabela motivos_quebra). Use
# services.motivos_quebra.nomes_ativos() para obter a lista atual.


def registrar_quebra(
    equipamento_id: str,
    local_id: str,
    tipo_ocorrencia: str,
    descricao: str,
    data_ocorrencia: str,
    responsavel_id: str | None = None,
) -> dict:
    """
    1) Cria a ocorrência.
    2) Atualiza o equipamento para Quebrada (localização permanece a mesma).
    3) Grava no histórico de movimentações.
    4) Verifica déficit da unidade e cria Substituição Pendente se necessário.
    """
    ocorrencia_resp = (
        supabase()
        .table("ocorrencias")
        .insert(
            {
                "equipamento_id": equipamento_id,
                "local_id": local_id,
                "tipo_ocorrencia": tipo_ocorrencia,
                "descricao": descricao,
                "data_ocorrencia": data_ocorrencia,
                "responsavel_id": responsavel_id,
                "status": "Aberta",
            }
        )
        .execute()
    )
    ocorrencia = ocorrencia_resp.data[0]

    svc_equip.atualizar_status_localizacao(
        equipamento_id, status=svc_equip.STATUS_QUEBRADA, localizacao_atual_id=local_id
    )

    svc_mov.registrar_movimentacao(
        equipamento_id=equipamento_id,
        tipo_movimentacao="Quebra",
        data_movimentacao=data_ocorrencia,
        origem_id=local_id,
        destino_id=local_id,
        responsavel_id=responsavel_id,
        observacao=f"Quebra registrada ({tipo_ocorrencia}). {descricao or ''}".strip(),
    )

    # ---- Regra 8: se houver déficit decorrente da quebra, cria substituição pendente ----
    deficit_atual = svc_dist.deficit_do_local(local_id)
    if deficit_atual > 0:
        _criar_substituicao_pendente(
            ocorrencia_id=ocorrencia["id"],
            equipamento_id=equipamento_id,
            local_id=local_id,
            data=data_ocorrencia,
        )

    return ocorrencia


def _criar_substituicao_pendente(ocorrencia_id: str, equipamento_id: str, local_id: str, data: str):
    supabase().table("substituicoes").insert(
        {
            "ocorrencia_id": ocorrencia_id,
            "equipamento_substituido_id": equipamento_id,
            "local_id": local_id,
            "motivo": "Quebra",
            "data_solicitacao": data,
            "status": "Pendente",
        }
    ).execute()


def listar_ocorrencias(limite: int = 200) -> list[dict]:
    resp = (
        supabase()
        .table("ocorrencias")
        .select("*")
        .order("data_ocorrencia", desc=True)
        .limit(limite)
        .execute()
    )
    return resp.data

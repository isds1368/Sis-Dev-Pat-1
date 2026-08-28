"""
Motivos de quebra — antes era uma lista fixa no código, agora é uma tabela
editável em Configurações → Cadastros (criar novos motivos e editar os
existentes, sem precisar mexer no código-fonte).
"""
from utils.database import supabase


def listar(apenas_ativos: bool = True) -> list[dict]:
    q = supabase().table("motivos_quebra").select("*").order("nome")
    if apenas_ativos:
        q = q.eq("ativo", True)
    return q.execute().data


def nomes_ativos() -> list[str]:
    return [m["nome"] for m in listar(apenas_ativos=True)]


def criar(nome: str) -> dict:
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe um nome para o motivo.")
    existente = supabase().table("motivos_quebra").select("id").eq("nome", nome).limit(1).execute()
    if existente.data:
        raise ValueError("Já existe um motivo com esse nome.")
    resp = supabase().table("motivos_quebra").insert({"nome": nome}).execute()
    return resp.data[0] if resp.data else None


def editar(motivo_id: str, nome: str | None = None, ativo: bool | None = None):
    payload = {}
    if nome is not None:
        payload["nome"] = nome.strip()
    if ativo is not None:
        payload["ativo"] = ativo
    if payload:
        supabase().table("motivos_quebra").update(payload).eq("id", motivo_id).execute()

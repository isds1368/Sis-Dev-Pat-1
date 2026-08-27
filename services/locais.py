from utils.database import supabase


def listar_locais(apenas_ativos: bool = True) -> list[dict]:
    q = supabase().table("locais").select("*").order("nome")
    if apenas_ativos:
        q = q.eq("ativo", True)
    return q.execute().data


def obter_local(local_id: str) -> dict | None:
    resp = supabase().table("locais").select("*").eq("id", local_id).limit(1).execute()
    return resp.data[0] if resp.data else None


def criar_local(nome: str, tipo: str) -> dict:
    resp = supabase().table("locais").insert({"nome": nome, "tipo": tipo}).execute()
    return resp.data[0] if resp.data else None


def mapa_id_para_nome() -> dict:
    return {l["id"]: l["nome"] for l in listar_locais(apenas_ativos=False)}

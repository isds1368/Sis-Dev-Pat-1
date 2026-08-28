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
    nome = nome.strip()
    if not nome:
        raise ValueError("Informe um nome para o local.")
    existente = supabase().table("locais").select("id").eq("nome", nome).limit(1).execute()
    if existente.data:
        raise ValueError("Já existe um local com esse nome.")
    resp = supabase().table("locais").insert({"nome": nome, "tipo": tipo}).execute()
    return resp.data[0] if resp.data else None


def editar_local(local_id: str, nome: str | None = None, tipo: str | None = None, ativo: bool | None = None):
    payload = {}
    if nome is not None:
        payload["nome"] = nome.strip()
    if tipo is not None:
        payload["tipo"] = tipo
    if ativo is not None:
        payload["ativo"] = ativo
    if payload:
        supabase().table("locais").update(payload).eq("id", local_id).execute()


def mapa_id_para_nome() -> dict:
    return {l["id"]: l["nome"] for l in listar_locais(apenas_ativos=False)}

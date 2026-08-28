import re

from utils.database import supabase

# Código só pode ter letras, números, hífen e underscore — bloqueia
# tentativas de injetar HTML/scripts ou caracteres de controle no campo.
PADRAO_CODIGO = re.compile(r"^[A-Za-z0-9\-_]{1,30}$")


def codigo_valido(codigo: str) -> bool:
    return bool(codigo) and bool(PADRAO_CODIGO.match(codigo.strip()))

STATUS_OPERACIONAL = "Em operação"
STATUS_MANUTENCAO = "Em manutenção"
STATUS_QUEBRADA = "Quebrada"
STATUS_AGUARDANDO_SUBSTITUICAO = "Aguardando substituição"
STATUS_SUBSTITUIDO = "Substituído"

TIPOS_EQUIPAMENTO = ["Manual", "Elétrica", "Semi-elétrica"]
PROPRIEDADES = ["Própria", "Alugada"]

# Status em que o equipamento não deve ser oferecido para movimentação ou
# para um novo registro de quebra — já está fora de operação por algum
# motivo relacionado a quebra/substituição.
STATUS_FORA_DE_OPERACAO = {STATUS_QUEBRADA, STATUS_AGUARDANDO_SUBSTITUICAO, STATUS_SUBSTITUIDO}

# Tipos de local que representam estoque parado (CD/Estoque), e não uma
# unidade operacional. O status "Disponível" foi removido: todo equipamento
# fora de STATUS_FORA_DE_OPERACAO é tratado como "Em operação", esteja ele
# de fato numa loja ou parado nesses locais. Para achar substitutos, quem
# precisa saber "está parado no estoque?" passa a olhar o TIPO do local
# atual, não mais um status separado.
TIPOS_LOCAL_ESTOQUE = {"CD", "Estoque"}


def listar_equipamentos(apenas_ativos: bool = True) -> list[dict]:
    q = supabase().table("equipamentos").select("*").order("codigo")
    if apenas_ativos:
        q = q.eq("ativo", True)
    return q.execute().data


def obter_equipamento(equipamento_id: str) -> dict | None:
    resp = (
        supabase()
        .table("equipamentos")
        .select("*")
        .eq("id", equipamento_id)
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else None


def obter_por_codigo(codigo: str, apenas_ativos: bool = True) -> dict | None:
    q = supabase().table("equipamentos").select("*").eq("codigo", codigo)
    if apenas_ativos:
        q = q.eq("ativo", True)
    resp = q.limit(1).execute()
    return resp.data[0] if resp.data else None


def codigo_existe(codigo: str) -> bool:
    """
    Verifica duplicidade apenas entre equipamentos ATIVOS. Um equipamento
    'Substituído' fica inativo e libera seu código para uma nova entrada —
    é a única forma de um código voltar a ser usado.
    """
    return obter_por_codigo(codigo, apenas_ativos=True) is not None


def proximo_codigo_sugerido() -> str:
    """Sugere o próximo código sequencial PAL-XXX (apenas sugestão; usuário pode alterar)."""
    equipamentos = listar_equipamentos(apenas_ativos=False)
    maior = 0
    for e in equipamentos:
        codigo = e.get("codigo", "")
        if codigo.startswith("PAL-"):
            try:
                num = int(codigo.split("-")[1])
                maior = max(maior, num)
            except (IndexError, ValueError):
                continue
    return f"PAL-{maior + 1:03d}"


def criar_equipamento(
    codigo: str,
    tipo: str,
    propriedade: str,
    fornecedor: str,
    data_chegada: str,
    localizacao_atual_id: str,
    status: str,
) -> dict:
    resp = (
        supabase()
        .table("equipamentos")
        .insert(
            {
                "codigo": codigo,
                "tipo": tipo,
                "propriedade": propriedade,
                "fornecedor": fornecedor,
                "data_chegada": data_chegada,
                "localizacao_atual_id": localizacao_atual_id,
                "status": status,
            }
        )
        .execute()
    )
    return resp.data[0] if resp.data else None


def atualizar_status_localizacao(equipamento_id: str, status: str, localizacao_atual_id: str | None = None):
    payload = {"status": status}
    if localizacao_atual_id is not None:
        payload["localizacao_atual_id"] = localizacao_atual_id
    supabase().table("equipamentos").update(payload).eq("id", equipamento_id).execute()


def retirar_equipamento(equipamento_id: str):
    """
    Marca o equipamento como Substituído e o desativa (ativo=false).
    A partir daqui ele nunca mais conta como disponível em nenhuma tela,
    permanece no histórico, e seu código fica livre para uma nova entrada.
    """
    supabase().table("equipamentos").update(
        {"status": STATUS_SUBSTITUIDO, "ativo": False}
    ).eq("id", equipamento_id).execute()


def contar_por_status() -> dict:
    equipamentos = listar_equipamentos()
    contagem = {
        STATUS_OPERACIONAL: 0,
        STATUS_MANUTENCAO: 0,
        STATUS_QUEBRADA: 0,
        STATUS_AGUARDANDO_SUBSTITUICAO: 0,
    }
    for e in equipamentos:
        s = e.get("status")
        if s in contagem:
            contagem[s] += 1
    contagem["Total"] = len(equipamentos)
    return contagem


def listar_em_estoque() -> list[dict]:
    """
    Equipamentos operacionais parados em CD/Estoque — a "reserva" que pode
    ser usada como substituto em uma quebra. Substitui o antigo filtro por
    status "Disponível": agora quem indica que um equipamento está parado
    no estoque (em vez de já alocado numa loja) é o TIPO do local atual.
    """
    from services import locais as svc_locais

    ids_estoque = {
        l["id"] for l in svc_locais.listar_locais(apenas_ativos=False) if l.get("tipo") in TIPOS_LOCAL_ESTOQUE
    }
    return [
        e
        for e in listar_equipamentos()
        if e.get("localizacao_atual_id") in ids_estoque and e.get("status") not in STATUS_FORA_DE_OPERACAO
    ]


def contar_por_propriedade() -> dict:
    equipamentos = listar_equipamentos()
    contagem = {"Própria": 0, "Alugada": 0}
    for e in equipamentos:
        p = e.get("propriedade")
        if p in contagem:
            contagem[p] += 1
    return contagem

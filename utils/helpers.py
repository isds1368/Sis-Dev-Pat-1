"""
Funções utilitárias puras: nenhuma delas fala com o banco.
"""
import html as _html
from datetime import date, datetime
from dateutil.relativedelta import relativedelta


# ------------------------------------------------------------
# Segurança: escape de HTML
# ------------------------------------------------------------
def esc(valor) -> str:
    """
    Escapa qualquer valor antes de ser inserido em HTML renderizado com
    unsafe_allow_html=True. Use SEMPRE em campos que vieram de entrada do
    usuário (código, fornecedor, nome, observação, descrição, nome de local
    etc.) para evitar XSS armazenado. Valores None/vazios viram '-'.
    """
    if valor is None or valor == "":
        return "-"
    return _html.escape(str(valor), quote=True)

# ------------------------------------------------------------
# Cores / badges de status
# ------------------------------------------------------------
STATUS_COR = {
    "Disponível": "azul",
    "Em operação": "verde",
    "Em manutenção": "laranja",
    "Quebrada": "vermelho",
    "Substituída": "cinza",
}

PROPRIEDADE_COR = {
    "Própria": "azul",
    "Alugada": "roxo",
}


def badge_html(texto: str, cor_classe: str) -> str:
    return f'<span class="badge badge-{cor_classe}">{texto}</span>'


def status_badge(status: str) -> str:
    cor = STATUS_COR.get(status, "cinza")
    return badge_html(status, cor)


def propriedade_badge(propriedade: str) -> str:
    cor = PROPRIEDADE_COR.get(propriedade, "cinza")
    return badge_html(propriedade.upper(), cor)


# ------------------------------------------------------------
# Datas / tempo de uso
# ------------------------------------------------------------
def parse_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def formatar_data_br(value) -> str:
    d = parse_date(value)
    return d.strftime("%d/%m/%Y") if d else "-"


def tempo_de_uso(data_chegada) -> str:
    """
    Retorna o tempo decorrido desde a chegada em formato legível:
    '1 ano e 7 meses', '5 meses', '3 dias'
    """
    inicio = parse_date(data_chegada)
    if not inicio:
        return "-"

    hoje = date.today()
    if inicio > hoje:
        return "-"

    diff = relativedelta(hoje, inicio)

    partes = []
    if diff.years > 0:
        partes.append(f"{diff.years} ano{'s' if diff.years != 1 else ''}")
    if diff.months > 0:
        partes.append(f"{diff.months} {'mês' if diff.months == 1 else 'meses'}")
    if not partes:
        dias = (hoje - inicio).days
        return f"{dias} dia{'s' if dias != 1 else ''}"

    return " e ".join(partes)


# ------------------------------------------------------------
# Cálculo de déficit
# ------------------------------------------------------------
def calcular_deficit(planejado: int, operacional: int) -> int:
    deficit = planejado - operacional
    return deficit if deficit > 0 else 0

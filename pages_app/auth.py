"""
Autenticação simples com hash seguro de senha (PBKDF2-HMAC-SHA256, biblioteca
padrão do Python — nenhuma senha é armazenada em texto puro).
"""
import hashlib
import re
import time
import secrets as pysecrets

import streamlit as st
from utils.database import supabase

PBKDF2_ITERATIONS = 200_000
SENHA_MIN_CARACTERES = 8
PADRAO_USUARIO = re.compile(r"^[a-zA-Z0-9._-]{3,40}$")


def hash_senha(senha: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = pysecrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", senha.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return hash_bytes.hex(), salt


def verificar_senha(senha: str, hash_armazenado: str, salt: str) -> bool:
    hash_calculado, _ = hash_senha(senha, salt)
    return pysecrets.compare_digest(hash_calculado, hash_armazenado)


def senha_forte(senha: str) -> tuple[bool, str]:
    """Validação mínima de robustez da senha (retorna (ok, mensagem))."""
    if len(senha) < SENHA_MIN_CARACTERES:
        return False, f"A senha deve ter pelo menos {SENHA_MIN_CARACTERES} caracteres."
    if senha.lower() == senha or senha.upper() == senha:
        return False, "Use letras maiúsculas e minúsculas na senha."
    if not any(c.isdigit() for c in senha):
        return False, "A senha deve conter pelo menos um número."
    return True, ""


def usuario_valido(usuario: str) -> bool:
    return bool(usuario) and bool(PADRAO_USUARIO.match(usuario.strip()))


PERFIS_VALIDOS = ("Administrador", "Supervisor")


def autenticar(usuario: str, senha: str) -> dict | None:
    resp = (
        supabase()
        .table("usuarios")
        .select("*")
        .eq("usuario", usuario)
        .eq("ativo", True)
        .limit(1)
        .execute()
    )
    if not resp.data:
        # Pequeno atraso mesmo quando o usuário não existe, para que a
        # resposta não sirva de oráculo (tempo constante ajuda contra
        # enumeração de usuários e reduz a velocidade de força bruta).
        time.sleep(0.4)
        return None

    registro = resp.data[0]
    if verificar_senha(senha, registro["senha_hash"], registro["salt"]):
        return registro

    time.sleep(0.4)
    return None


def criar_usuario(
    usuario: str,
    senha: str,
    nome: str,
    perfil: str = "Administrador",
    local_id: str | None = None,
) -> dict:
    usuario = usuario.strip()
    if not usuario_valido(usuario):
        raise ValueError(
            "Login inválido. Use de 3 a 40 caracteres: letras, números, ponto, hífen ou underscore."
        )

    if perfil not in PERFIS_VALIDOS:
        raise ValueError("Perfil inválido.")
    if perfil == "Supervisor" and not local_id:
        raise ValueError("Selecione o local do Supervisor.")

    ok, motivo = senha_forte(senha)
    if not ok:
        raise ValueError(motivo)

    existente = (
        supabase().table("usuarios").select("id").eq("usuario", usuario).limit(1).execute()
    )
    if existente.data:
        raise ValueError("Já existe um usuário com esse login.")

    hash_val, salt = hash_senha(senha)
    resp = (
        supabase()
        .table("usuarios")
        .insert(
            {
                "usuario": usuario,
                "senha_hash": hash_val,
                "salt": salt,
                "nome": nome.strip(),
                "perfil": perfil,
                "local_id": local_id if perfil == "Supervisor" else None,
                # Senha provisória definida por quem está concedendo o
                # acesso: a pessoa é obrigada a trocá-la no primeiro login.
                "deve_trocar_senha": True,
            }
        )
        .execute()
    )
    return resp.data[0] if resp.data else None


def listar_usuarios() -> list[dict]:
    """Retorna usuários sem os campos sensíveis (hash/salt nunca saem daqui)."""
    resp = (
        supabase()
        .table("usuarios")
        .select("id, usuario, nome, perfil, local_id, ativo, created_at")
        .order("usuario")
        .execute()
    )
    return resp.data


def definir_status_usuario(usuario_id: str, ativo: bool):
    """Desativa/reativa acesso. Nunca apaga o registro (preserva responsabilidade
    histórica em movimentações/ocorrências que referenciam este usuário)."""
    supabase().table("usuarios").update({"ativo": ativo}).eq("id", usuario_id).execute()


def alterar_propria_senha(usuario_id: str, senha_atual: str, nova_senha: str) -> tuple[bool, str]:
    resp = supabase().table("usuarios").select("*").eq("id", usuario_id).limit(1).execute()
    if not resp.data:
        return False, "Usuário não encontrado."

    registro = resp.data[0]
    if not verificar_senha(senha_atual, registro["senha_hash"], registro["salt"]):
        return False, "Senha atual incorreta."

    ok, motivo = senha_forte(nova_senha)
    if not ok:
        return False, motivo

    hash_val, salt = hash_senha(nova_senha)
    supabase().table("usuarios").update(
        {"senha_hash": hash_val, "salt": salt, "deve_trocar_senha": False}
    ).eq("id", usuario_id).execute()
    return True, "Senha alterada com sucesso."


def concluir_primeiro_acesso(usuario_id: str, nova_senha: str) -> tuple[bool, str]:
    """
    Fluxo do módulo de primeiro acesso: a pessoa já provou que tem a senha
    provisória (passou pelo autenticar() para chegar aqui), então troca a
    senha sem pedir a senha atual de novo, e libera o acesso normal ao
    marcar deve_trocar_senha = False.
    """
    ok, motivo = senha_forte(nova_senha)
    if not ok:
        return False, motivo

    hash_val, salt = hash_senha(nova_senha)
    supabase().table("usuarios").update(
        {"senha_hash": hash_val, "salt": salt, "deve_trocar_senha": False}
    ).eq("id", usuario_id).execute()
    return True, "Senha definida com sucesso."


def usuario_logado() -> dict | None:
    return st.session_state.get("usuario_logado")


def logout():
    for chave in ["usuario_logado", "pagina_atual"]:
        st.session_state.pop(chave, None)


def exigir_login():
    """Bloqueia a renderização da página se não houver sessão ativa."""
    if not usuario_logado():
        st.stop()

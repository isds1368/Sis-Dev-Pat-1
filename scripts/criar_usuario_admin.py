"""
Script de linha de comando para criar o primeiro usuário Administrador.
Não existe tela de cadastro de usuário na interface (fora do escopo do
sistema, que é operacional e não deve crescer em complexidade).

Uso:
    export SUPABASE_URL="https://SEU-PROJETO.supabase.co"
    export SUPABASE_KEY="sua-chave"
    python scripts/criar_usuario_admin.py
"""
import os
import sys
from getpass import getpass

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Usa as mesmas credenciais via variáveis de ambiente (sem depender de st.secrets)
from supabase import create_client
import hashlib
import secrets as pysecrets

PBKDF2_ITERATIONS = 200_000


def hash_senha(senha: str):
    salt = pysecrets.token_hex(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return hash_bytes.hex(), salt


def senha_forte(senha: str):
    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres."
    if senha.lower() == senha or senha.upper() == senha:
        return False, "Use letras maiúsculas e minúsculas na senha."
    if not any(c.isdigit() for c in senha):
        return False, "A senha deve conter pelo menos um número."
    return True, ""


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Defina SUPABASE_URL e SUPABASE_KEY (use a chave service_role) antes de rodar este script.")
        sys.exit(1)

    client = create_client(url, key)

    usuario = input("Usuário (login): ").strip()
    nome = input("Nome completo: ").strip()
    senha = getpass("Senha: ")
    senha_confirma = getpass("Confirme a senha: ")

    if senha != senha_confirma:
        print("As senhas não coincidem.")
        sys.exit(1)

    ok, motivo = senha_forte(senha)
    if not ok:
        print(motivo)
        sys.exit(1)

    hash_val, salt = hash_senha(senha)

    resp = client.table("usuarios").insert(
        {
            "usuario": usuario,
            "senha_hash": hash_val,
            "salt": salt,
            "nome": nome,
            "perfil": "Administrador",
            # Senha definida aqui pelo operador do script, não pelo dono da
            # conta: o módulo de primeiro acesso obriga a troca no 1º login.
            "deve_trocar_senha": True,
        }
    ).execute()

    if resp.data:
        print(f"Usuário '{usuario}' criado com sucesso.")
    else:
        print("Falha ao criar usuário.")


if __name__ == "__main__":
    main()

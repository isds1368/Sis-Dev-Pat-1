"""
Conexão única com o Supabase.
Credenciais nunca ficam no código: vêm de st.secrets (ou variáveis de ambiente
como fallback, útil para rodar localmente com um .env exportado no shell).
"""
import os
import streamlit as st
from supabase import create_client, Client


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
    key = st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))

    if not url or not key:
        st.error(
            "Credenciais do Supabase não configuradas. "
            "Defina SUPABASE_URL e SUPABASE_KEY em .streamlit/secrets.toml."
        )
        st.stop()

    return create_client(url, key)


def supabase() -> Client:
    return get_client()

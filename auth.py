from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from pwdlib import PasswordHash

from database import Repositorio

COOKIE_NAME = "contratacoes_session"
SESSION_SECONDS = 8 * 60 * 60
password_hash = PasswordHash.recommended()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def validar_senha_nova(senha: str) -> None:
    if len(senha) < 10:
        raise ValueError("A senha deve possuir pelo menos 10 caracteres.")
    if senha.lower() == senha or senha.upper() == senha:
        raise ValueError("A senha deve conter letras maiúsculas e minúsculas.")
    if not any(caractere.isdigit() for caractere in senha):
        raise ValueError("A senha deve conter pelo menos um número.")


def perfil_autocadastro(total_usuarios: int) -> str:
    return "admin" if total_usuarios == 0 else "editor"


class ServicoAutenticacao:
    def __init__(self, repositorio: Repositorio) -> None:
        self.repositorio = repositorio

    def criar_usuario(
        self, nome: str, login: str, senha: str, perfil: str = "editor", secretaria: str = ""
    ) -> dict[str, Any]:
        validar_senha_nova(senha)
        return self.repositorio.criar_usuario(
            nome, login, password_hash.hash(senha), perfil, secretaria
        )

    def autenticar(self, login: str, senha: str) -> dict[str, Any] | None:
        usuario = self.repositorio.obter_usuario_por_login(login)
        if not usuario or not usuario["ativo"]:
            return None
        if not password_hash.verify(senha, usuario["senha_hash"]):
            return None
        return {
            chave: valor
            for chave, valor in usuario.items()
            if chave != "senha_hash"
        }

    def atualizar_usuario(self, usuario_id: int, nome: str, login: str, perfil: str,
                          secretaria: str, ativo: bool, senha: str = ""):
        senha_hash = ""
        if senha:
            validar_senha_nova(senha)
            senha_hash = password_hash.hash(senha)
        return self.repositorio.atualizar_usuario(
            usuario_id, nome, login, perfil, secretaria, ativo, senha_hash)

    def iniciar_sessao(self, usuario_id: int) -> str:
        token = secrets.token_urlsafe(32)
        expira = datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)
        self.repositorio.criar_sessao(
            hash_token(token), usuario_id, expira.isoformat()
        )
        self.repositorio.registrar_auditoria(
            usuario_id, "login", "sessao", detalhes={"resultado": "sucesso"}
        )
        return token

    def usuario_da_sessao(self, token: str | None) -> dict[str, Any] | None:
        if not token:
            return None
        return self.repositorio.obter_usuario_por_sessao(hash_token(token))

    def encerrar_sessao(self, token: str | None, usuario_id: int | None) -> None:
        if token:
            self.repositorio.remover_sessao(hash_token(token))
        if usuario_id:
            self.repositorio.registrar_auditoria(
                usuario_id, "logout", "sessao", detalhes={"resultado": "sucesso"}
            )

"""Copia com segurança o banco SQLite atual para um banco MySQL vazio."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from database import Repositorio  # noqa: E402


TABELAS = ("usuarios", "contratacoes", "documentos", "sessoes", "auditoria", "requisicoes")


def migrar(origem: Path, destino_url: str) -> dict[str, int]:
    if not origem.is_file():
        raise ValueError(f"Banco SQLite não encontrado: {origem}")
    destino = Repositorio(destino_url)
    totais = {}
    with sqlite3.connect(origem) as sqlite:
        sqlite.row_factory = sqlite3.Row
        with destino.conectar() as mysql:
            ocupadas = {
                tabela: mysql.execute(f"SELECT COUNT(*) AS total FROM {tabela}").fetchone()["total"]
                for tabela in TABELAS
            }
            if any(ocupadas.values()):
                raise ValueError("O banco MySQL de destino deve estar vazio para evitar duplicação de dados.")
            mysql.execute("SET FOREIGN_KEY_CHECKS = 0")
            try:
                for tabela in TABELAS:
                    linhas = [dict(linha) for linha in sqlite.execute(f"SELECT * FROM {tabela}")]
                    totais[tabela] = len(linhas)
                    if not linhas:
                        continue
                    colunas = list(linhas[0])
                    marcadores = ", ".join("?" for _ in colunas)
                    sql = f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({marcadores})"
                    for linha in linhas:
                        mysql.execute(sql, tuple(linha[coluna] for coluna in colunas))
            finally:
                mysql.execute("SET FOREIGN_KEY_CHECKS = 1")
    return totais


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origem", type=Path, default=Path("data/contratacoes.db"))
    parser.add_argument("--mysql-url", default=os.getenv("DATABASE_URL"))
    argumentos = parser.parse_args()
    if not argumentos.mysql_url or not argumentos.mysql_url.startswith(("mysql://", "mysql+pymysql://")):
        parser.error("Informe --mysql-url ou a variável DATABASE_URL com uma conexão MySQL.")
    resultado = migrar(argumentos.origem, argumentos.mysql_url)
    print("Migração concluída: " + ", ".join(f"{tabela}={total}" for tabela, total in resultado.items()))

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import pymysql


def agora() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConexaoMySQL:
    """Adapta o PyMySQL à interface já usada pelo repositório SQLite."""

    def __init__(self, conexao) -> None:
        self.conexao = conexao

    def execute(self, sql: str, parametros: tuple = ()):
        cursor = self.conexao.cursor()
        cursor.execute(sql.replace("?", "%s"), parametros)
        return cursor

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traceback):
        if tipo is None:
            self.conexao.commit()
        else:
            self.conexao.rollback()
        return False

    def close(self) -> None:
        self.conexao.close()


class Repositorio:
    def __init__(self, caminho: Path | str) -> None:
        valor = str(caminho)
        self.mysql = valor.startswith(("mysql://", "mysql+pymysql://"))
        self.database_url = valor
        self.caminho = None if self.mysql else Path(caminho)
        if self.caminho:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self.inicializar()

    def conectar(self):
        if self.mysql:
            url = urlparse(self.database_url.replace("mysql+pymysql://", "mysql://", 1))
            return ConexaoMySQL(
                pymysql.connect(
                    host=url.hostname or "localhost",
                    port=url.port or 3306,
                    user=unquote(url.username or ""),
                    password=unquote(url.password or ""),
                    database=(url.path or "").lstrip("/"),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=False,
                )
            )
        conexao = sqlite3.connect(self.caminho, timeout=10)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def inicializar(self) -> None:
        if self.mysql:
            self._inicializar_mysql()
            return
        with closing(self.conectar()) as conexao, conexao:
            conexao.executescript(
                """
                CREATE TABLE IF NOT EXISTS contratacoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    secretaria TEXT NOT NULL,
                    objeto TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'rascunho',
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS documentos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contratacao_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    subtipo TEXT NOT NULL,
                    versao INTEGER NOT NULL,
                    dados_json TEXT NOT NULL,
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (contratacao_id) REFERENCES contratacoes(id),
                    UNIQUE (contratacao_id, tipo, subtipo, versao)
                );

                CREATE INDEX IF NOT EXISTS idx_documentos_contratacao
                ON documentos (contratacao_id, criado_em DESC);

                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    login TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    senha_hash TEXT NOT NULL,
                    perfil TEXT NOT NULL CHECK (perfil IN ('admin', 'editor')),
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessoes (
                    token_hash TEXT PRIMARY KEY,
                    usuario_id INTEGER NOT NULL,
                    criado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );

                CREATE TABLE IF NOT EXISTS auditoria (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER,
                    acao TEXT NOT NULL,
                    recurso_tipo TEXT NOT NULL,
                    recurso_id INTEGER,
                    detalhes_json TEXT NOT NULL DEFAULT '{}',
                    criado_em TEXT NOT NULL,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );

                CREATE INDEX IF NOT EXISTS idx_auditoria_recurso
                ON auditoria (recurso_tipo, recurso_id, criado_em DESC);

                CREATE TABLE IF NOT EXISTS requisicoes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    placa TEXT NOT NULL,
                    numero_orcamento TEXT NOT NULL DEFAULT '',
                    secretaria TEXT NOT NULL,
                    tipo TEXT NOT NULL,
                    fornecedor TEXT NOT NULL DEFAULT '',
                    valor_total REAL NOT NULL,
                    emitida_em TEXT NOT NULL,
                    usuario_id INTEGER,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                );

                CREATE INDEX IF NOT EXISTS idx_requisicoes_mes_placa
                ON requisicoes (emitida_em, placa);
                """
            )
            colunas_contratacoes = {
                linha["name"]
                for linha in conexao.execute("PRAGMA table_info(contratacoes)")
            }
            if "usuario_id" not in colunas_contratacoes:
                conexao.execute("ALTER TABLE contratacoes ADD COLUMN usuario_id INTEGER")
            colunas_documentos = {
                linha["name"]
                for linha in conexao.execute("PRAGMA table_info(documentos)")
            }
            if "usuario_id" not in colunas_documentos:
                conexao.execute("ALTER TABLE documentos ADD COLUMN usuario_id INTEGER")
            colunas_usuarios = {linha["name"] for linha in conexao.execute("PRAGMA table_info(usuarios)")}
            if "secretaria" not in colunas_usuarios:
                conexao.execute("ALTER TABLE usuarios ADD COLUMN secretaria TEXT NOT NULL DEFAULT ''")

    def _inicializar_mysql(self) -> None:
        comandos = [
            """CREATE TABLE IF NOT EXISTS usuarios (
                id BIGINT PRIMARY KEY AUTO_INCREMENT, nome VARCHAR(200) NOT NULL,
                login VARCHAR(120) NOT NULL UNIQUE, senha_hash TEXT NOT NULL,
                perfil ENUM('admin','editor') NOT NULL, secretaria VARCHAR(255) NOT NULL DEFAULT '', ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em VARCHAR(40) NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS contratacoes (
                id BIGINT PRIMARY KEY AUTO_INCREMENT, titulo VARCHAR(255) NOT NULL,
                secretaria VARCHAR(255) NOT NULL, objeto TEXT NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'rascunho', criado_em VARCHAR(40) NOT NULL,
                atualizado_em VARCHAR(40) NOT NULL, usuario_id BIGINT NULL,
                CONSTRAINT fk_contratacoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id))
                ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS documentos (
                id BIGINT PRIMARY KEY AUTO_INCREMENT, contratacao_id BIGINT NOT NULL,
                tipo VARCHAR(30) NOT NULL, subtipo VARCHAR(120) NOT NULL, versao INT NOT NULL,
                dados_json LONGTEXT NOT NULL, criado_em VARCHAR(40) NOT NULL, usuario_id BIGINT NULL,
                CONSTRAINT fk_documentos_contratacao FOREIGN KEY (contratacao_id) REFERENCES contratacoes(id),
                CONSTRAINT fk_documentos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                UNIQUE KEY uq_documento_versao (contratacao_id, tipo, subtipo, versao),
                INDEX idx_documentos_contratacao (contratacao_id, criado_em))
                ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS sessoes (
                token_hash VARCHAR(128) PRIMARY KEY, usuario_id BIGINT NOT NULL,
                criado_em VARCHAR(40) NOT NULL, expira_em VARCHAR(40) NOT NULL,
                CONSTRAINT fk_sessoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                INDEX idx_sessoes_expiracao (expira_em))
                ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS auditoria (
                id BIGINT PRIMARY KEY AUTO_INCREMENT, usuario_id BIGINT NULL,
                acao VARCHAR(80) NOT NULL, recurso_tipo VARCHAR(80) NOT NULL,
                recurso_id BIGINT NULL, detalhes_json LONGTEXT NOT NULL, criado_em VARCHAR(40) NOT NULL,
                CONSTRAINT fk_auditoria_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                INDEX idx_auditoria_recurso (recurso_tipo, recurso_id, criado_em))
                ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
            """CREATE TABLE IF NOT EXISTS requisicoes (
                id BIGINT PRIMARY KEY AUTO_INCREMENT, placa VARCHAR(20) NOT NULL,
                numero_orcamento VARCHAR(80) NOT NULL DEFAULT '', secretaria VARCHAR(255) NOT NULL,
                tipo VARCHAR(30) NOT NULL, fornecedor VARCHAR(255) NOT NULL DEFAULT '',
                valor_total DECIMAL(14,2) NOT NULL, emitida_em VARCHAR(40) NOT NULL,
                usuario_id BIGINT NULL,
                CONSTRAINT fk_requisicoes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
                INDEX idx_requisicoes_mes_placa (emitida_em, placa))
                ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
        ]
        with closing(self.conectar()) as conexao, conexao:
            for comando in comandos:
                conexao.execute(comando)

    def total_usuarios(self) -> int:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute("SELECT COUNT(*) AS total FROM usuarios").fetchone()
            return int(linha["total"] if isinstance(linha, dict) else linha[0])

    def criar_usuario(
        self, nome: str, login: str, senha_hash: str, perfil: str = "editor", secretaria: str = ""
    ) -> dict[str, Any]:
        nome = nome.strip()
        login = login.strip().lower()
        if not nome or not login:
            raise ValueError("Informe o nome e o usuário de acesso.")
        if perfil not in {"admin", "editor"}:
            raise ValueError("Perfil de usuário inválido.")
        secretaria = secretaria.strip()
        try:
            with closing(self.conectar()) as conexao, conexao:
                cursor = conexao.execute(
                    """
                    INSERT INTO usuarios
                        (nome, login, senha_hash, perfil, secretaria, ativo, criado_em)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                    """,
                    (nome, login, senha_hash, perfil, secretaria, agora()),
                )
                identificador = int(cursor.lastrowid)
        except (sqlite3.IntegrityError, pymysql.err.IntegrityError) as exc:
            raise ValueError("Esse usuário de acesso já está cadastrado.") from exc
        return self.obter_usuario(identificador)

    def obter_usuario(self, usuario_id: int) -> dict[str, Any]:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                """
                SELECT id, nome, login, perfil, secretaria, ativo, criado_em
                FROM usuarios WHERE id = ?
                """,
                (usuario_id,),
            ).fetchone()
        if not linha:
            raise ValueError("Usuário não encontrado.")
        return dict(linha)

    def obter_usuario_por_login(self, login: str) -> dict[str, Any] | None:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                "SELECT * FROM usuarios WHERE LOWER(login) = LOWER(?)",
                (login.strip(),),
            ).fetchone()
        return dict(linha) if linha else None

    def listar_usuarios(self) -> list[dict[str, Any]]:
        with closing(self.conectar()) as conexao, conexao:
            linhas = conexao.execute(
                """
                SELECT id, nome, login, perfil, secretaria, ativo, criado_em
                FROM usuarios ORDER BY nome
                """
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def atualizar_usuario(self, usuario_id: int, nome: str, login: str, perfil: str,
                          secretaria: str, ativo: bool, senha_hash: str = "") -> dict[str, Any]:
        nome, login, secretaria = nome.strip(), login.strip().lower(), secretaria.strip()
        if not nome or not login or perfil not in {"admin", "editor"}:
            raise ValueError("Dados do usuário inválidos.")
        if perfil == "editor" and not secretaria:
            raise ValueError("Selecione a secretaria de acesso do usuário.")
        try:
            with closing(self.conectar()) as conexao, conexao:
                if senha_hash:
                    conexao.execute("""UPDATE usuarios SET nome=?, login=?, perfil=?, secretaria=?,
                                      ativo=?, senha_hash=? WHERE id=?""",
                                    (nome, login, perfil, secretaria, int(ativo), senha_hash, usuario_id))
                else:
                    conexao.execute("""UPDATE usuarios SET nome=?, login=?, perfil=?, secretaria=?,
                                      ativo=? WHERE id=?""",
                                    (nome, login, perfil, secretaria, int(ativo), usuario_id))
        except (sqlite3.IntegrityError, pymysql.err.IntegrityError) as exc:
            raise ValueError("Esse usuário de acesso já está cadastrado.") from exc
        return self.obter_usuario(usuario_id)

    def criar_sessao(
        self, token_hash: str, usuario_id: int, expira_em: str
    ) -> None:
        with closing(self.conectar()) as conexao, conexao:
            conexao.execute(
                "DELETE FROM sessoes WHERE expira_em <= ?", (agora(),)
            )
            conexao.execute(
                """
                INSERT INTO sessoes (token_hash, usuario_id, criado_em, expira_em)
                VALUES (?, ?, ?, ?)
                """,
                (token_hash, usuario_id, agora(), expira_em),
            )

    def obter_usuario_por_sessao(self, token_hash: str) -> dict[str, Any] | None:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                """
                SELECT u.id, u.nome, u.login, u.perfil, u.secretaria, u.ativo, u.criado_em
                FROM sessoes s
                JOIN usuarios u ON u.id = s.usuario_id
                WHERE s.token_hash = ? AND s.expira_em > ? AND u.ativo = 1
                """,
                (token_hash, agora()),
            ).fetchone()
        return dict(linha) if linha else None

    def remover_sessao(self, token_hash: str) -> None:
        with closing(self.conectar()) as conexao, conexao:
            conexao.execute("DELETE FROM sessoes WHERE token_hash = ?", (token_hash,))

    def registrar_auditoria(
        self,
        usuario_id: int | None,
        acao: str,
        recurso_tipo: str,
        recurso_id: int | None = None,
        detalhes: dict[str, Any] | None = None,
    ) -> None:
        with closing(self.conectar()) as conexao, conexao:
            conexao.execute(
                """
                INSERT INTO auditoria
                    (usuario_id, acao, recurso_tipo, recurso_id, detalhes_json, criado_em)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    usuario_id,
                    acao,
                    recurso_tipo,
                    recurso_id,
                    json.dumps(detalhes or {}, ensure_ascii=False),
                    agora(),
                ),
            )

    def criar_contratacao(
        self,
        titulo: str,
        secretaria: str,
        objeto: str = "",
        usuario_id: int | None = None,
    ) -> dict[str, Any]:
        titulo = titulo.strip()
        secretaria = secretaria.strip()
        if not titulo or not secretaria:
            raise ValueError("Informe o título e a secretaria da contratação.")
        instante = agora()
        with closing(self.conectar()) as conexao, conexao:
            cursor = conexao.execute(
                """
                INSERT INTO contratacoes
                    (titulo, secretaria, objeto, status, criado_em, atualizado_em, usuario_id)
                VALUES (?, ?, ?, 'rascunho', ?, ?, ?)
                """,
                (titulo, secretaria, objeto.strip(), instante, instante, usuario_id),
            )
            identificador = cursor.lastrowid
            conexao.execute(
                """
                INSERT INTO auditoria
                    (usuario_id, acao, recurso_tipo, recurso_id, detalhes_json, criado_em)
                VALUES (?, 'criar', 'contratacao', ?, '{}', ?)
                """,
                (usuario_id, identificador, instante),
            )
        return self.obter_contratacao(int(identificador))

    def listar_contratacoes(self, usuario_id: int | None = None, secretaria: str = "") -> list[dict[str, Any]]:
        filtros, parametros = [], []
        if usuario_id is not None:
            filtros.append("c.usuario_id = ?"); parametros.append(usuario_id)
        if secretaria:
            filtros.append("c.secretaria = ?"); parametros.append(secretaria)
        filtro = " WHERE " + " AND ".join(filtros) if filtros else ""
        with closing(self.conectar()) as conexao, conexao:
            linhas = conexao.execute(
                f"""
                SELECT c.*, u.nome AS criado_por,
                       (SELECT COUNT(*) FROM documentos d
                        WHERE d.contratacao_id = c.id) AS total_documentos
                FROM contratacoes c
                LEFT JOIN usuarios u ON u.id = c.usuario_id
                {filtro}
                ORDER BY c.atualizado_em DESC, c.id DESC
                """, tuple(parametros)
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def obter_contratacao(self, identificador: int) -> dict[str, Any]:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                "SELECT * FROM contratacoes WHERE id = ?", (identificador,)
            ).fetchone()
        if not linha:
            raise ValueError("Contratação não encontrada.")
        return dict(linha)

    def usuario_pode_acessar_contratacao(self, contratacao_id: int, usuario_id: int, admin: bool = False) -> bool:
        if admin:
            return True
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                "SELECT 1 FROM contratacoes WHERE id = ? AND usuario_id = ?",
                (contratacao_id, usuario_id),
            ).fetchone()
        return bool(linha)

    def usuario_pode_acessar_documento(self, documento_id: int, usuario_id: int, admin: bool = False) -> bool:
        if admin:
            return True
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                """SELECT 1 FROM documentos d JOIN contratacoes c ON c.id = d.contratacao_id
                   WHERE d.id = ? AND c.usuario_id = ?""", (documento_id, usuario_id)
            ).fetchone()
        return bool(linha)

    def salvar_documento(
        self,
        contratacao_id: int,
        tipo: str,
        subtipo: str,
        dados: dict[str, Any],
        usuario_id: int | None = None,
    ) -> dict[str, Any]:
        if tipo not in {"dfd", "etp", "tr"}:
            raise ValueError("Tipo de documento inválido.")
        if not subtipo.strip():
            raise ValueError("Informe o subtipo do documento.")
        instante = agora()
        serializado = json.dumps(dados, ensure_ascii=False, separators=(",", ":"))
        with closing(self.conectar()) as conexao, conexao:
            conexao.execute("START TRANSACTION" if self.mysql else "BEGIN IMMEDIATE")
            existe = conexao.execute(
                "SELECT 1 FROM contratacoes WHERE id = ?", (contratacao_id,)
            ).fetchone()
            if not existe:
                raise ValueError("Contratação não encontrada.")
            linha = conexao.execute(
                """
                SELECT COALESCE(MAX(versao), 0) + 1 AS proxima
                FROM documentos
                WHERE contratacao_id = ? AND tipo = ? AND subtipo = ?
                """,
                (contratacao_id, tipo, subtipo),
            ).fetchone()
            versao = int(linha["proxima"])
            cursor = conexao.execute(
                """
                INSERT INTO documentos
                    (contratacao_id, tipo, subtipo, versao, dados_json, criado_em, usuario_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contratacao_id,
                    tipo,
                    subtipo,
                    versao,
                    serializado,
                    instante,
                    usuario_id,
                ),
            )
            conexao.execute(
                "UPDATE contratacoes SET atualizado_em = ? WHERE id = ?",
                (instante, contratacao_id),
            )
            documento_id = int(cursor.lastrowid)
            conexao.execute(
                """
                INSERT INTO auditoria
                    (usuario_id, acao, recurso_tipo, recurso_id, detalhes_json, criado_em)
                VALUES (?, 'salvar_versao', 'documento', ?, ?, ?)
                """,
                (
                    usuario_id,
                    documento_id,
                    json.dumps(
                        {
                            "contratacao_id": contratacao_id,
                            "tipo": tipo,
                            "subtipo": subtipo,
                            "versao": versao,
                        },
                        ensure_ascii=False,
                    ),
                    instante,
                ),
            )
        return self.obter_documento(documento_id)

    def listar_documentos(self, contratacao_id: int) -> list[dict[str, Any]]:
        self.obter_contratacao(contratacao_id)
        with closing(self.conectar()) as conexao, conexao:
            linhas = conexao.execute(
                """
                SELECT d.id, d.contratacao_id, d.tipo, d.subtipo, d.versao,
                       d.criado_em, d.usuario_id, u.nome AS criado_por
                FROM documentos d
                LEFT JOIN usuarios u ON u.id = d.usuario_id
                WHERE d.contratacao_id = ?
                ORDER BY d.criado_em DESC, d.id DESC
                """,
                (contratacao_id,),
            ).fetchall()
        return [dict(linha) for linha in linhas]

    def obter_documento(self, documento_id: int) -> dict[str, Any]:
        with closing(self.conectar()) as conexao, conexao:
            linha = conexao.execute(
                """
                SELECT d.*, u.nome AS criado_por
                FROM documentos d
                LEFT JOIN usuarios u ON u.id = d.usuario_id
                WHERE d.id = ?
                """,
                (documento_id,),
            ).fetchone()
        if not linha:
            raise ValueError("Documento não encontrado.")
        resultado = dict(linha)
        resultado["dados"] = json.loads(resultado.pop("dados_json"))
        return resultado

    def registrar_requisicao(self, dados: dict[str, Any], usuario_id: int | None) -> int:
        with closing(self.conectar()) as conexao, conexao:
            cursor = conexao.execute(
                """INSERT INTO requisicoes
                   (placa, numero_orcamento, secretaria, tipo, fornecedor,
                    valor_total, emitida_em, usuario_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (dados["placa"], dados.get("numero_orcamento", ""),
                 dados["secretaria"], dados["tipo"], dados.get("fornecedor", ""),
                 dados["valor_total"], dados["emitida_em"], usuario_id),
            )
            return int(cursor.lastrowid)

    def relatorio_requisicoes(self, ano: int, mes: int, secretaria: str = "", usuario_id: int | None = None) -> list[dict[str, Any]]:
        prefixo = f"{ano:04d}-{mes:02d}"
        sql = """SELECT placa,
                    SUM(CASE WHEN tipo = 'material' THEN valor_total ELSE 0 END) AS materiais,
                    SUM(CASE WHEN tipo = 'servico' THEN valor_total ELSE 0 END) AS servicos,
                    SUM(valor_total) AS total, COUNT(*) AS requisicoes
                 FROM requisicoes WHERE emitida_em LIKE ?"""
        parametros: list[Any] = [prefixo + "%"]
        if secretaria:
            sql += " AND secretaria = ?"
            parametros.append(secretaria)
        if usuario_id is not None:
            sql += " AND usuario_id = ?"
            parametros.append(usuario_id)
        sql += " GROUP BY placa ORDER BY placa"
        with closing(self.conectar()) as conexao, conexao:
            linhas = conexao.execute(sql, tuple(parametros)).fetchall()
        return [dict(linha) for linha in linhas]

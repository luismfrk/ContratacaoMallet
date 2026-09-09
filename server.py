import os
import json
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import Any
from io import BytesIO

from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import gerar_dfd, listar_tipos_dfd
from docx_exporter import gerar_dfd_docx
from etp import gerar_etp
from etp_docx_exporter import gerar_etp_docx
from etp_obras import gerar_etp_obras
from etp_obras_docx_exporter import gerar_etp_obras_docx
from tr import gerar_tr, listar_tipos_tr
from tr_docx_exporter import gerar_tr_docx
from requisicao import (ler_orcamento, gerar_requisicao, ler_relacao_pneus,
                        gerar_requisicoes_pneus, ler_demonstrativo_impressoras,
                        gerar_requisicao_impressoras, ler_saldos_materiais_construcao,
                        gerar_requisicao_material_construcao, gerar_requisicoes_material_construcao)
from relatorio_requisicoes import gerar_relatorio_requisicoes
from database import Repositorio
from auth import (
    COOKIE_NAME,
    SESSION_SECONDS,
    ServicoAutenticacao,
    usuario_pode_acessar_secretaria,
    perfil_autocadastro,
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
repositorio = Repositorio(
    os.getenv("DATABASE_URL") or BASE_DIR / "data" / "contratacoes.db"
)
autenticacao = ServicoAutenticacao(repositorio)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

app = FastAPI(title="Assistente de Contratações Públicas", version="0.1.0",
              docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class DFDRequest(BaseModel):
    tipo: str
    dados: dict[str, Any]


class ETPRequest(BaseModel):
    dados: dict[str, Any]


class TRRequest(BaseModel):
    tipo: str
    dados: dict[str, Any]


class ContratacaoRequest(BaseModel):
    titulo: str
    secretaria: str
    objeto: str = ""


class DocumentoRequest(BaseModel):
    tipo: str
    subtipo: str
    dados: dict[str, Any]


class LoginRequest(BaseModel):
    login: str
    senha: str


class UsuarioRequest(BaseModel):
    nome: str
    login: str
    senha: str
    perfil: str = "editor"
    secretaria: str = ""


class UsuarioUpdateRequest(BaseModel):
    nome: str
    login: str
    perfil: str
    secretaria: str = ""
    ativo: bool = True
    senha: str = ""


class RequisicaoRequest(BaseModel):
    tipo: str
    dados: dict[str, Any]


@app.middleware("http")
async def proteger_api(request: Request, call_next):
    caminho = request.url.path
    rotas_publicas = {
        "/api/auth/status",
        "/api/auth/setup",
        "/api/auth/login",
    }
    if caminho.startswith("/api/") and caminho not in rotas_publicas:
        usuario = autenticacao.usuario_da_sessao(request.cookies.get(COOKIE_NAME))
        if not usuario:
            return JSONResponse(
                status_code=401,
                content={"detail": "Sua sessão expirou. Entre novamente."},
            )
        request.state.usuario = usuario
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        cookie = response.headers.get("set-cookie", "")
        if cookie and "secure" not in cookie.lower():
            response.headers["set-cookie"] = cookie + "; Secure"
    return response


def definir_cookie(response: Response, token: str, seguro: bool = False) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE or seguro,
        samesite="lax",
        path="/",
    )


def exigir_admin(request: Request) -> dict[str, Any]:
    usuario = request.state.usuario
    if usuario["perfil"] != "admin":
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem gerenciar usuários."
        )
    return usuario


def exigir_acesso_secretaria(usuario: dict[str, Any], secretaria: str) -> None:
    if not usuario_pode_acessar_secretaria(usuario, secretaria):
        raise HTTPException(
            status_code=403,
            detail="Você não possui acesso à secretaria informada.",
        )


def exigir_acesso_contratacao(usuario: dict[str, Any], contratacao_id: int) -> dict[str, Any]:
    try:
        contratacao = repositorio.obter_contratacao(contratacao_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    exigir_acesso_secretaria(usuario, contratacao["secretaria"])
    return contratacao


def exigir_acesso_dados_documento(usuario: dict[str, Any], dados: dict[str, Any]) -> None:
    secretaria = next((str(dados.get(campo) or "").strip()
                       for campo in ("secretaria", "unidade_requisitante", "solicitante")
                       if dados.get(campo)), "")
    exigir_acesso_secretaria(usuario, secretaria)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/auth/status")
def auth_status(request: Request) -> dict[str, Any]:
    if repositorio.total_usuarios() == 0:
        return {"setup_required": True, "authenticated": False, "user": None}
    usuario = autenticacao.usuario_da_sessao(request.cookies.get(COOKIE_NAME))
    return {
        "setup_required": False,
        "authenticated": bool(usuario),
        "user": usuario,
    }


@app.post("/api/auth/setup")
def auth_setup(request: UsuarioRequest, response: Response) -> dict[str, Any]:
    if repositorio.total_usuarios() != 0:
        raise HTTPException(status_code=409, detail="O primeiro acesso já foi configurado.")
    try:
        usuario = autenticacao.criar_usuario(
            request.nome, request.login, request.senha, "admin"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    token = autenticacao.iniciar_sessao(usuario["id"])
    definir_cookie(response, token)
    return {"success": True, "user": usuario}


@app.post("/api/auth/register")
def auth_register(request: UsuarioRequest, response: Response) -> dict[str, Any]:
    raise HTTPException(status_code=403, detail="O cadastro público está desativado. Solicite acesso ao administrador.")


@app.post("/api/auth/login")
def auth_login(request: LoginRequest, response: Response) -> dict[str, Any]:
    usuario = autenticacao.autenticar(request.login, request.senha)
    if not usuario:
        repositorio.registrar_auditoria(
            None,
            "login_falhou",
            "sessao",
            detalhes={"login": request.login.strip().lower()},
        )
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos.")
    token = autenticacao.iniciar_sessao(usuario["id"])
    definir_cookie(response, token)
    return {"success": True, "user": usuario}


@app.post("/api/auth/logout")
def auth_logout(request: Request, response: Response) -> dict[str, bool]:
    usuario = request.state.usuario
    autenticacao.encerrar_sessao(
        request.cookies.get(COOKIE_NAME), usuario["id"]
    )
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"success": True}


@app.get("/api/usuarios")
def listar_usuarios(request: Request) -> dict[str, Any]:
    exigir_admin(request)
    return {"usuarios": repositorio.listar_usuarios()}


@app.post("/api/usuarios")
def criar_usuario(request: Request, dados: UsuarioRequest) -> dict[str, Any]:
    administrador = exigir_admin(request)
    if dados.perfil == "editor" and not dados.secretaria.strip():
        raise HTTPException(status_code=400, detail="Selecione a secretaria de acesso do usuário.")
    try:
        usuario = autenticacao.criar_usuario(
            dados.nome, dados.login, dados.senha, dados.perfil, dados.secretaria
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repositorio.registrar_auditoria(
        administrador["id"],
        "criar",
        "usuario",
        usuario["id"],
        {"perfil": usuario["perfil"]},
    )
    return {"success": True, "usuario": usuario}


@app.put("/api/usuarios/{usuario_id}")
def atualizar_usuario(usuario_id: int, request: Request, dados: UsuarioUpdateRequest) -> dict[str, Any]:
    administrador = exigir_admin(request)
    if usuario_id == administrador["id"] and (not dados.ativo or dados.perfil != "admin"):
        raise HTTPException(status_code=400, detail="Você não pode desativar ou remover seu próprio perfil de administrador.")
    try:
        usuario = autenticacao.atualizar_usuario(usuario_id, dados.nome, dados.login,
            dados.perfil, "" if dados.perfil == "admin" else dados.secretaria,
            dados.ativo, dados.senha)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    repositorio.registrar_auditoria(administrador["id"], "atualizar", "usuario", usuario_id,
        {"perfil": usuario["perfil"], "secretaria": usuario["secretaria"], "ativo": usuario["ativo"]})
    return {"success": True, "usuario": usuario}


@app.get("/api/contratacoes")
def listar_contratacoes(request: Request) -> dict[str, Any]:
    usuario = request.state.usuario
    if usuario["perfil"] != "admin" and not usuario.get("secretaria"):
        return {"contratacoes": []}
    contratacoes = repositorio.listar_contratacoes()
    if usuario["perfil"] != "admin":
        contratacoes = [item for item in contratacoes
                        if usuario_pode_acessar_secretaria(usuario, item["secretaria"])]
    return {"contratacoes": contratacoes}


@app.post("/api/contratacoes")
def criar_contratacao(request: Request, dados: ContratacaoRequest) -> dict[str, Any]:
    exigir_acesso_secretaria(request.state.usuario, dados.secretaria)
    try:
        contratacao = repositorio.criar_contratacao(
            dados.titulo,
            dados.secretaria,
            dados.objeto,
            request.state.usuario["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "contratacao": contratacao}


@app.get("/api/contratacoes/{contratacao_id}/documentos")
def listar_documentos(contratacao_id: int, request: Request) -> dict[str, Any]:
    usuario = request.state.usuario
    exigir_acesso_contratacao(usuario, contratacao_id)
    try:
        documentos = repositorio.listar_documentos(contratacao_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"documentos": documentos}


@app.get("/api/documentos/{documento_id}")
def obter_documento(documento_id: int, request: Request) -> dict[str, Any]:
    usuario = request.state.usuario
    try:
        documento = repositorio.obter_documento(documento_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    exigir_acesso_contratacao(usuario, documento["contratacao_id"])
    return {"documento": documento}


@app.post("/api/contratacoes/{contratacao_id}/documentos")
def salvar_documento(
    contratacao_id: int, request: Request, dados: DocumentoRequest
) -> dict[str, Any]:
    usuario = request.state.usuario
    exigir_acesso_contratacao(usuario, contratacao_id)
    exigir_acesso_dados_documento(usuario, dados.dados)
    try:
        documento = repositorio.salvar_documento(
            contratacao_id,
            dados.tipo,
            dados.subtipo,
            dados.dados,
            request.state.usuario["id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "documento": documento}


@app.get("/api/dfd/tipos")
def tipos_dfd() -> dict[str, Any]:
    return {"tipos": listar_tipos_dfd()}


@app.post("/api/dfd/generate")
def generate_dfd(request: Request, dados_request: DFDRequest) -> dict[str, Any]:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        resultado = gerar_dfd(dados_request.tipo, dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/dfd/download")
def download_dfd(request: Request, dados_request: DFDRequest) -> StreamingResponse:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        conteudo, nome_arquivo = gerar_dfd_docx(dados_request.tipo, dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {"Content-Disposition": f'attachment; filename="{nome_arquivo}"'}
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers=headers,
    )


@app.post("/api/etp/generate")
def generate_etp(request: Request, dados_request: ETPRequest) -> dict[str, Any]:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        resultado = gerar_etp(dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/etp/download")
def download_etp(request: Request, dados_request: ETPRequest) -> StreamingResponse:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        conteudo, nome_arquivo = gerar_etp_docx(dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@app.post("/api/etp/obras/generate")
def generate_etp_obras(request: Request, dados_request: ETPRequest) -> dict[str, Any]:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        resultado = gerar_etp_obras(dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/etp/obras/download")
def download_etp_obras(request: Request, dados_request: ETPRequest) -> StreamingResponse:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        conteudo, nome_arquivo = gerar_etp_obras_docx(dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@app.get("/api/tr/tipos")
def tipos_tr() -> dict[str, Any]:
    return {"tipos": listar_tipos_tr()}


@app.post("/api/tr/generate")
def generate_tr(request: Request, dados_request: TRRequest) -> dict[str, Any]:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        resultado = gerar_tr(dados_request.tipo, dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/tr/download")
def download_tr(request: Request, dados_request: TRRequest) -> StreamingResponse:
    exigir_acesso_dados_documento(request.state.usuario, dados_request.dados)
    try:
        conteudo, nome_arquivo = gerar_tr_docx(dados_request.tipo, dados_request.dados)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@app.post("/api/requisicoes/importar")
async def importar_orcamento(arquivo: UploadFile = File(...)) -> dict[str, Any]:
    if not arquivo.filename or not arquivo.filename.lower().endswith((".pdf", ".xlsx")):
        raise HTTPException(status_code=400, detail="Envie um orçamento no formato PDF ou .xlsx.")
    try:
        resultado = ler_orcamento(await arquivo.read(), arquivo.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/requisicoes/pneus/importar")
async def importar_relacao_pneus(arquivo: UploadFile = File(...)) -> dict[str, Any]:
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie a relação dos itens no formato PDF.")
    conteudo = await arquivo.read(10 * 1024 * 1024 + 1)
    try:
        resultado = ler_relacao_pneus(conteudo)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/requisicoes/materiais-construcao/saldos")
async def importar_saldos_materiais_construcao(arquivo: UploadFile = File(...)) -> dict[str, Any]:
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie o controle de saldo no formato PDF.")
    try:
        resultado = ler_saldos_materiais_construcao(await arquivo.read(10 * 1024 * 1024 + 1))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/requisicoes/materiais-construcao/download")
def download_requisicao_material_construcao(
    request: Request, dados_request: RequisicaoRequest
) -> StreamingResponse:
    try:
        dados = dados_request.dados
        secretaria = str(dados.get("secretaria") or "").strip()
        exigir_acesso_secretaria(request.state.usuario, secretaria)
        conteudo, nome, total = gerar_requisicao_material_construcao(dados)
        lote = dados.get("lote") or {}
        repositorio.registrar_requisicao({
            "placa": f"LOTE {lote.get('numero', '')}",
            "numero_orcamento": dados.get("numero_orcamento", ""),
            "secretaria": secretaria, "tipo": "material_construcao",
            "fornecedor": dados.get("fornecedor") or lote.get("fornecedor", ""),
            "valor_total": total, "emitida_em": datetime.now().isoformat(),
        }, request.state.usuario["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )


@app.post("/api/requisicoes/materiais-construcao/download-zip")
def download_requisicoes_material_construcao_zip(
    request: Request, dados_request: RequisicaoRequest
) -> StreamingResponse:
    try:
        dados = dados_request.dados
        secretaria = str(dados.get("secretaria") or "").strip()
        exigir_acesso_secretaria(request.state.usuario, secretaria)
        conteudo, nome, registros = gerar_requisicoes_material_construcao(dados)
        for registro in registros:
            lote = registro["lote"]
            repositorio.registrar_requisicao({
                "placa": f"LOTE {lote.get('numero', '')}",
                "numero_orcamento": dados.get("numero_orcamento", ""),
                "secretaria": secretaria, "tipo": "material_construcao",
                "fornecedor": registro["fornecedor"],
                "valor_total": registro["valor_total"],
                "emitida_em": datetime.now().isoformat(),
            }, request.state.usuario["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo), media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )


@app.post("/api/requisicoes/impressoras/importar")
async def importar_demonstrativo_impressoras(
    request: Request, arquivo: UploadFile = File(...), secretaria: str = Form("")
) -> dict[str, Any]:
    if not arquivo.filename or not arquivo.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie o demonstrativo no formato PDF.")
    exigir_acesso_secretaria(request.state.usuario, secretaria)
    try:
        resultado = ler_demonstrativo_impressoras(await arquivo.read(10 * 1024 * 1024 + 1))
        resultado["grupos"] = [g for g in resultado["grupos"] if not secretaria or g["secretaria"] == secretaria]
        if secretaria and not resultado["grupos"]:
            raise ValueError(f"O demonstrativo não possui produção para a secretaria {secretaria}.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "resultado": resultado}


@app.post("/api/requisicoes/impressoras/download")
async def download_requisicao_impressoras(
    request: Request, arquivo: UploadFile = File(...), dados_json: str = Form(...)
) -> StreamingResponse:
    try:
        dados = json.loads(dados_json)
        secretaria = str(dados.get("secretaria") or "").strip()
        exigir_acesso_secretaria(request.state.usuario, secretaria)
        conteudo, nome, total = gerar_requisicao_impressoras(
            await arquivo.read(10 * 1024 * 1024 + 1), dados
        )
        repositorio.registrar_requisicao({
            "placa": "IMPRESSORAS", "numero_orcamento": dados.get("contrato", ""),
            "secretaria": secretaria, "tipo": "impressora",
            "fornecedor": "ETP PRINTERS LTDA", "valor_total": total,
            "emitida_em": datetime.now().isoformat(),
        }, request.state.usuario["id"])
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )


@app.post("/api/requisicoes/pneus/download")
async def download_requisicoes_pneus(
    request: Request, arquivo: UploadFile = File(...), dados_json: str = Form(...)
) -> StreamingResponse:
    try:
        dados = json.loads(dados_json)
        if not isinstance(dados, dict):
            raise ValueError("Dados da requisição de pneus inválidos.")
        secretaria = str(dados.get("secretaria") or "").strip()
        exigir_acesso_secretaria(request.state.usuario, secretaria)
        conteudo_pdf = await arquivo.read(10 * 1024 * 1024 + 1)
        conteudo, nome, registros = gerar_requisicoes_pneus(conteudo_pdf, dados)
        for registro in registros:
            repositorio.registrar_requisicao({
                "placa": str(dados.get("placa") or "PNEUS").strip().upper(),
                "numero_orcamento": "",
                "secretaria": secretaria,
                "tipo": "pneu",
                "fornecedor": registro["fornecedor"],
                "valor_total": registro["valor_total"],
                "emitida_em": datetime.now().isoformat(),
            }, request.state.usuario["id"])
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo), media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )


@app.post("/api/requisicoes/download")
def download_requisicao(request: Request, dados_request: RequisicaoRequest) -> StreamingResponse:
    try:
        dados = dados_request.dados
        secretaria = str(dados.get("secretaria") or "").strip()
        exigir_acesso_secretaria(request.state.usuario, secretaria)
        conteudo, nome = gerar_requisicao(dados_request.tipo, dados)
        desconto_geral = float(dados.get("desconto") or 0)
        total = 0.0
        for item in dados.get("itens", []):
            desconto = float(item.get("desconto", desconto_geral) or 0)
            total += float(item.get("quantidade", 0)) * float(item.get("valor_unitario", 0)) * (1 - desconto / 100)
        placa = str(dados.get("placa") or "").strip().upper()
        if not placa or not secretaria:
            raise ValueError("Informe a placa e selecione a secretaria para registrar a requisição.")
        repositorio.registrar_requisicao({
            "placa": placa, "numero_orcamento": dados.get("numero_orcamento", ""),
            "secretaria": secretaria, "tipo": dados_request.tipo,
            "fornecedor": dados.get("fornecedor", ""), "valor_total": round(total, 2),
            "emitida_em": datetime.now().isoformat(),
        }, request.state.usuario["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return StreamingResponse(
        BytesIO(conteudo),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"},
    )


@app.get("/api/requisicoes/relatorio")
def relatorio_requisicoes(request: Request, ano: int, mes: int, secretaria: str = "") -> StreamingResponse:
    if ano < 2020 or ano > 2100 or mes < 1 or mes > 12:
        raise HTTPException(status_code=400, detail="Informe um mês e ano válidos.")
    usuario = request.state.usuario
    if usuario["perfil"] != "admin":
        secretaria = str(usuario.get("secretaria") or "")
        exigir_acesso_secretaria(usuario, secretaria)
    linhas = repositorio.relatorio_requisicoes(
        ano, mes, secretaria)
    conteudo, nome = gerar_relatorio_requisicoes(linhas, ano, mes, secretaria)
    return StreamingResponse(BytesIO(conteudo), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(nome)}"})

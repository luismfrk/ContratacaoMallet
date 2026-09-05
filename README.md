# Assistente de Contratações Públicas — Mallet

Sistema FastAPI com frontend em JavaScript para elaborar e gerenciar documentos de contratações públicas. A aplicação oferece autenticação, DFD, ETP, termo de referência, requisições, relatórios e exportação para DOCX.

## Execução local

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn server:app --reload
```

Acesse `http://localhost:8000`. O health check é `GET /health`.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Docker

```bash
docker build -t contratacao-mallet .
docker run --rm -p 8000:8000 --env-file .env contratacao-mallet
```

O pipeline em `.github/workflows/ci-cd.yml` testa a aplicação, publica `ghcr.io/luismfrk/contratacaomallet` e atualiza automaticamente o serviço em <https://contratacao-mallet.onrender.com>. Consulte `docs/MANUAL-CICD.md`.

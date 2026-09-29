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

## Assistência por IA

As sugestões de redação usam a AIMLAPI somente pelo backend. Defina as variáveis
no ambiente do servidor (nunca no JavaScript nem em arquivos versionados):

```env
AI_PROVIDER=groq
AI_MODEL=openai/gpt-oss-120b
AI_API_KEY=sua_chave
AI_TIMEOUT_SECONDS=45
```

`AI_PROVIDER` aceita `groq` ou `aimlapi`; quando `AI_MODEL` não for informado, o
sistema escolhe o modelo padrão do provedor. Com o provedor configurado, os campos
textuais de DFD, ETP e TR exibem o botão
**Sugerir com IA**. O texto só substitui o conteúdo do campo depois do aceite do
usuário. Reinicie o servidor após alterar as variáveis.

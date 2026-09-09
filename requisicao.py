from __future__ import annotations

from copy import copy
from io import BytesIO
from pathlib import Path
import re
import unicodedata
from difflib import get_close_matches
from datetime import date
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook
from openpyxl.utils.cell import range_boundaries
import pdfplumber


BASE_DIR = Path(__file__).resolve().parent
MODELOS = {
    "material": BASE_DIR / "modelo_material.xlsx",
    "servico": BASE_DIR / "modelo_servico.xlsx",
}
MODELO_PNEU = BASE_DIR / "modelo_pneu.xlsx"
MODELO_IMPRESSORA = BASE_DIR / "modelo_impressora.xlsx"
MODELO_CONSTRUCAO = BASE_DIR / "modelo_material_construcao.xlsx"
NUMERO_RELACAO = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2,3}")

SECRETARIAS_IMPRESSORAS = {
    "administracao": "Administração", "agricultura": "Agropecuária e Abastecimento",
    "cultura e turismo": "Cultura e Turismo", "defesa civil": "Defesa Civil",
    "educacao": "Educação", "esportes": "Esportes",
    "familia": "Família e Desenvolvimento Social", "fazenda": "Fazenda",
    "gabinete": "Gabinete", "industria e comercio": "Indústria e Comércio",
    "obras": "Obras e Serviços Públicos", "planejamento": "Planejamento", "saude": "Saúde",
}


def _texto(valor) -> str:
    return "" if valor is None else str(valor).strip()


def _normalizar(valor) -> str:
    texto = unicodedata.normalize("NFKD", _texto(valor)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.lower())


def _numero(valor, padrao=0.0) -> float:
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = _texto(valor).replace("R$", "").replace("%", "").replace(" ", "")
    if not texto:
        return padrao
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return padrao


def _texto_planilha(valor) -> str:
    texto = _texto(valor)
    return "'" + texto if texto.startswith(("=", "+", "-", "@")) else texto


def _secretaria_canonica(valor: str) -> str:
    chave = re.sub(r"[^a-z ]", "", _normalizar(valor)).strip()
    if chave in SECRETARIAS_IMPRESSORAS:
        return SECRETARIAS_IMPRESSORAS[chave]
    aproximada = get_close_matches(chave, SECRETARIAS_IMPRESSORAS, n=1, cutoff=.68)
    return SECRETARIAS_IMPRESSORAS[aproximada[0]] if aproximada else _texto(valor)


def _producao_inteira(valor) -> int:
    texto = re.sub(r"\D", "", _texto(valor))
    return int(texto or 0)


def ler_demonstrativo_impressoras(conteudo: bytes) -> dict:
    if len(conteudo) > 10 * 1024 * 1024:
        raise ValueError("O demonstrativo deve possuir no máximo 10 MB.")
    registros = []
    try:
        with pdfplumber.open(BytesIO(conteudo)) as pdf:
            for pagina in pdf.pages:
                for tabela in pagina.extract_tables() or []:
                    for linha in tabela:
                        if not linha or len(linha) < 9 or _normalizar(linha[0]) in {"serial", "etp printers"}:
                            continue
                        faturamento = _texto(linha[8])
                        tarifa = re.search(r"R\$\s*([\d.,]+)", faturamento, re.I)
                        categoria = "colorida" if "cor" in _normalizar(faturamento) else "pb" if "pb" in _normalizar(faturamento) else ""
                        producao = _producao_inteira(linha[6])
                        if not tarifa or not categoria or not _texto(linha[1]) or not _texto(linha[0]):
                            continue
                        registros.append({
                            "serial": _texto(linha[0]), "secretaria": _secretaria_canonica(linha[1]),
                            "local": _texto(linha[2]), "modelo": _texto(linha[3]),
                            "producao": producao, "categoria": categoria,
                            "valor_unitario": _numero(tarifa.group(1)),
                        })
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Envie um demonstrativo de impressoras em PDF válido.") from exc
    if not registros:
        raise ValueError("Não foi possível identificar impressoras no demonstrativo enviado.")
    grupos = {}
    for item in registros:
        chave = (item["secretaria"], item["categoria"], item["valor_unitario"])
        grupo = grupos.setdefault(chave, {"secretaria": item["secretaria"], "categoria": item["categoria"],
                                          "valor_unitario": item["valor_unitario"], "producao": 0,
                                          "quantidade_impressoras": 0, "total": 0})
        grupo["producao"] += item["producao"]
        grupo["quantidade_impressoras"] += 1
    for grupo in grupos.values():
        grupo["total"] = round(grupo["producao"] * grupo["valor_unitario"], 2)
    return {"itens": registros, "grupos": list(grupos.values()),
            "secretarias": sorted({x["secretaria"] for x in registros}),
            "total": round(sum(x["producao"] * x["valor_unitario"] for x in registros), 2)}


def gerar_requisicao_impressoras(conteudo_pdf: bytes, dados: dict) -> tuple[bytes, str, float]:
    demonstrativo = ler_demonstrativo_impressoras(conteudo_pdf)
    secretaria = _secretaria_canonica(dados.get("secretaria"))
    grupos = [g for g in demonstrativo["grupos"] if g["secretaria"] == secretaria]
    if not grupos:
        raise ValueError(f"O demonstrativo não possui produção para a secretaria {secretaria}.")
    categorias = {g["categoria"] for g in grupos}
    if len(categorias) != 1:
        raise ValueError("Envie demonstrativos separados para impressões PB e coloridas.")
    workbook = load_workbook(MODELO_IMPRESSORA)
    ws = workbook.active
    destino = _texto(dados.get("destino")) or f"Secretaria Municipal de {secretaria}"
    contrato = _texto(dados.get("contrato"))
    fonte = _texto(dados.get("fonte_recurso"))
    ws["A21"] = ("Solicitamos que seja emitida Autorização de Fornecimento dos materiais/serviços "
                 f"abaixo descritos destinados à: {destino}     Contrato: {contrato}     Fonte: {fonte}")
    for linha in range(24, 33):
        for coluna in range(1, 6):
            ws.cell(linha, coluna).value = None
    categoria = next(iter(categorias))
    for linha, grupo in enumerate(sorted(grupos, key=lambda g: g["valor_unitario"], reverse=True), 24):
        ws.cell(linha, 1).value = linha - 23
        ws.cell(linha, 2).value = ("Impressões coloridas" if categoria == "colorida" else
                                   ("Multifuncional Laser P&B" if grupo["valor_unitario"] >= .09 else "Impressora Laser P&B Monocromática"))
        ws.cell(linha, 3).value = grupo["producao"]
        ws.cell(linha, 4).value = grupo["valor_unitario"]
        ws.cell(linha, 5).value = f"=C{linha}*D{linha}"
    ws["E33"] = "=SUM(E24:E32)"
    hoje = date.today()
    ws["A33"] = f"Mallet/PR, {hoje.day:02d}/{hoje.month:02d}/{hoje.year}."
    if _texto(dados.get("responsavel_nome")):
        ws["B38"] = _texto_planilha(dados.get("responsavel_nome"))
    if _texto(dados.get("responsavel_cargo")):
        ws["B39"] = _texto_planilha(dados.get("responsavel_cargo"))
    if _texto(dados.get("responsavel_ato")):
        ws["B40"] = _texto_planilha(dados.get("responsavel_ato"))
    total = round(sum(g["total"] for g in grupos), 2)
    saida = BytesIO()
    workbook.save(saida)
    sufixo = "COLORIDA" if categoria == "colorida" else "PB"
    nome_secretaria = re.sub(r"[^A-Za-z0-9_-]+", "_", _normalizar(secretaria)).strip("_").upper()
    return saida.getvalue(), f"REQUISICAO_IMPRESSORAS_{sufixo}_{nome_secretaria}.xlsx", total


def _ignorar_linha_relacao(linha: str) -> bool:
    inicios = (
        "ESTADO DO PARANÁ", "Página:", "Data:", "PREFEITURA MUNICIPAL",
        "RELAÇÃO DOS ITENS", "Parâmetros:", "Tipo de instrumento:",
        "Processo administrativo:", "VALOR UNIT.", "N° ITEM", "TOTAL:",
        "Protocolo:", "Desenvolvedor:",
    )
    return not linha or linha.startswith(inicios)


def _analisar_textos_relacao_pneus(paginas: list[str]) -> list[dict]:
    itens: list[dict] = []
    fornecedor = ""
    contratacao = ""
    descricao_pendente = ""
    item_atual: dict | None = None

    for texto_pagina in paginas:
        for bruta in texto_pagina.splitlines():
            linha = re.sub(r"\s+", " ", bruta).strip()
            cabecalho = re.match(
                r"^Contratação:\s*([^ ]+).*?Fornecedor:\s*(.+)$", linha, re.I
            )
            if cabecalho:
                contratacao = cabecalho.group(1).strip()
                fornecedor = cabecalho.group(2).strip()
                descricao_pendente = ""
                item_atual = None
                continue

            partes = linha.split()
            numeros_finais: list[str] = []
            for parte in reversed(partes):
                if NUMERO_RELACAO.fullmatch(parte):
                    numeros_finais.append(parte)
                else:
                    break
            if partes and partes[0].isdigit() and len(numeros_finais) == 10:
                numeros = list(reversed(numeros_finais))
                trecho = " ".join(partes[1:-10]).strip()
                descricao = trecho or descricao_pendente
                item_atual = {
                    "numero": int(partes[0]),
                    "descricao": descricao,
                    "fornecedor": fornecedor,
                    "contratacao": contratacao,
                    "valor_unitario": _numero(numeros[1]),
                    "quantidade_contratada": _numero(numeros[2]),
                    "quantidade_comprada": _numero(numeros[4]),
                    "saldo_quantidade": _numero(numeros[5]),
                    "saldo_valor": _numero(numeros[9]),
                }
                itens.append(item_atual)
                descricao_pendente = ""
                continue

            if _ignorar_linha_relacao(linha):
                continue
            if linha.upper().startswith(("PNEU", "PNEUS", "CÂMARA", "CAMARA", "PROTETOR")):
                descricao_pendente = linha
                item_atual = None
            elif descricao_pendente:
                descricao_pendente += " " + linha
            elif item_atual is not None:
                item_atual["descricao"] = (item_atual["descricao"] + " " + linha).strip()

    unicos = {item["numero"]: item for item in itens if item["fornecedor"] and item["descricao"]}
    return [unicos[numero] for numero in sorted(unicos)]


def ler_relacao_pneus(conteudo: bytes) -> dict:
    if len(conteudo) > 10 * 1024 * 1024:
        raise ValueError("A relação de pneus deve possuir no máximo 10 MB.")
    try:
        with pdfplumber.open(BytesIO(conteudo)) as pdf:
            if len(pdf.pages) > 100:
                raise ValueError("A relação de pneus deve possuir no máximo 100 páginas.")
            paginas = [(pagina.extract_text() or "") for pagina in pdf.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Envie uma relação de itens em PDF válida.") from exc
    itens = _analisar_textos_relacao_pneus(paginas)
    if not itens:
        raise ValueError("Não foi possível identificar os itens na relação enviada.")
    return {"itens": itens, "total_itens": len(itens)}


def ler_saldos_materiais_construcao(conteudo: bytes) -> dict:
    """Lê os lotes de materiais e seus saldos financeiros no relatório da Betha."""
    if len(conteudo) > 10 * 1024 * 1024:
        raise ValueError("O controle de saldo deve possuir no máximo 10 MB.")
    try:
        with pdfplumber.open(BytesIO(conteudo)) as pdf:
            if len(pdf.pages) > 100:
                raise ValueError("O controle de saldo deve possuir no máximo 100 páginas.")
            paginas = [pagina.extract_text() or "" for pagina in pdf.pages]
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Envie um controle de saldo em PDF válido.") from exc

    lotes = []
    fornecedor = contrato = processo = ""
    for pagina in paginas:
        for bruta in pagina.splitlines():
            linha = re.sub(r"\s+", " ", bruta).strip()
            cabecalho = re.match(r"^Contratação:\s*([^ ]+).*?Fornecedor:\s*(.+)$", linha, re.I)
            if cabecalho:
                contrato, fornecedor = cabecalho.group(1).strip(), cabecalho.group(2).strip()
                continue
            encontrado_processo = re.search(r"Processo administrativo:\s*([^ ]+)", linha, re.I)
            if encontrado_processo:
                processo = encontrado_processo.group(1).strip()
                continue
            partes = linha.split()
            numeros = []
            for parte in reversed(partes):
                if NUMERO_RELACAO.fullmatch(parte):
                    numeros.append(parte)
                else:
                    break
            if not partes or not partes[0].isdigit() or len(numeros) != 10:
                continue
            numeros = list(reversed(numeros))
            descricao = " ".join(partes[1:-10]).strip()
            if not descricao or not fornecedor:
                continue
            lotes.append({
                "numero": int(partes[0]), "descricao": descricao,
                "fornecedor": fornecedor, "contrato": contrato, "processo": processo,
                "saldo_quantidade": _numero(numeros[5]), "saldo_valor": _numero(numeros[9]),
            })
    if not lotes:
        raise ValueError("Não foi possível identificar lotes e saldos no relatório enviado.")
    return {"lotes": lotes, "total_lotes": len(lotes)}


def gerar_requisicao_material_construcao(dados: dict) -> tuple[bytes, str, float]:
    itens = dados.get("itens") or []
    if not itens or len(itens) > 29:
        raise ValueError("Informe de 1 a 29 itens para este modelo de requisição.")
    lote = dados.get("lote") or {}
    saldo = _numero(lote.get("saldo_valor"))
    desconto_geral = _numero(dados.get("desconto"))
    if desconto_geral > 1:
        desconto_geral /= 100
    total = 0.0
    for item in itens:
        desconto = _numero(item.get("desconto"), desconto_geral)
        if desconto > 1:
            desconto /= 100
        total += _numero(item.get("quantidade")) * _numero(item.get("valor_unitario")) * (1 - desconto)
    total = round(total, 2)
    if saldo <= 0:
        raise ValueError("Selecione um lote com saldo financeiro disponível.")
    if total > saldo + .005:
        raise ValueError(f"O total líquido de R$ {total:,.2f} ultrapassa o saldo do lote de R$ {saldo:,.2f}.")

    workbook = load_workbook(MODELO_CONSTRUCAO)
    ws = workbook.active
    extras = max(0, len(itens) - 7)
    if extras:
        mesclagens = [str(intervalo) for intervalo in ws.merged_cells.ranges]
        for intervalo in mesclagens:
            ws.unmerge_cells(intervalo)
        ws.move_range("A32:I58", rows=extras, cols=0, translate=True)
        for intervalo in mesclagens:
            limites = range_boundaries(intervalo)
            min_col, min_row, max_col, max_row = limites
            if min_row >= 32:
                min_row += extras
                max_row += extras
            ws.merge_cells(start_row=min_row, start_column=min_col,
                           end_row=max_row, end_column=max_col)
        for linha in range(32, 32 + extras):
            ws.row_dimensions[linha].height = ws.row_dimensions[31].height
            for coluna in range(1, 10):
                origem = ws.cell(31, coluna)
                destino_celula = ws.cell(linha, coluna)
                destino_celula._style = copy(origem._style)
                destino_celula.number_format = origem.number_format
    fornecedor = _texto(dados.get("fornecedor") or lote.get("fornecedor"))
    contrato = _texto(lote.get("contrato"))
    descricao_lote = _texto(lote.get("descricao"))
    ws["B13"] = f"Solicitamos que seja emitida Autorização de Fornecimento dos materiais/serviços abaixo descritos destinados a                                                                {_texto(dados.get('destino'))}"
    ws["B15"] = f"Empresa: {fornecedor}"
    ws["B17"] = f"Endereço: {_texto(dados.get('endereco'))}"
    ws["B19"] = f"Cidade: {_texto(dados.get('cidade'))}"
    ws["B21"] = (f"Fonte/Recurso: {_texto(dados.get('fonte_recurso'))}                   "
                 f"Contrato nº {contrato}                              "
                 f"Lote: {lote.get('numero', '')} - {descricao_lote}")
    ultima_linha_item = 31 + extras
    for linha in range(25, ultima_linha_item + 1):
        for coluna in range(2, 9):
            ws.cell(linha, coluna).value = None
    for linha, item in enumerate(itens, 25):
        desconto = _numero(item.get("desconto"), desconto_geral)
        if desconto > 1:
            desconto /= 100
        ws.cell(linha, 2).value = _numero(item.get("quantidade"))
        ws.cell(linha, 3).value = _texto_planilha(item.get("codigo"))
        ws.cell(linha, 4).value = _texto_planilha(item.get("descricao"))
        ws.cell(linha, 5).value = _numero(item.get("valor_unitario"))
        ws.cell(linha, 6).value = f"=B{linha}*E{linha}"
        ws.cell(linha, 7).value = desconto
        ws.cell(linha, 8).value = f"=F{linha}-(F{linha}*G{linha})"
    linha_total = 32 + extras
    ws.cell(linha_total, 7).value = "TOTAL"
    ws.cell(linha_total, 8).value = f"=SUM(H25:H{ultima_linha_item})"
    hoje = date.today()
    ws.cell(37 + extras, 6).value = f"Mallet/PR, {hoje.day:02d}/{hoje.month:02d}/{hoje.year}."
    if _texto(dados.get("responsavel_nome")):
        ws.cell(43 + extras, 4).value = _texto_planilha(dados.get("responsavel_nome"))
    if _texto(dados.get("responsavel_cargo")):
        cargo = _texto(dados.get("responsavel_cargo"))
        ato = _texto(dados.get("responsavel_ato"))
        ws.cell(44 + extras, 4).value = _texto_planilha(f"{cargo}{' - ' + ato if ato else ''}")
    saida = BytesIO()
    workbook.save(saida)
    nome = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{contrato}_{descricao_lote}").strip("_")[:80]
    return saida.getvalue(), f"REQUISICAO_MATERIAIS_{nome}.xlsx", total


def gerar_requisicoes_material_construcao(dados: dict) -> tuple[bytes, str, list[dict]]:
    grupos = dados.get("grupos_lotes") or []
    if not grupos:
        raise ValueError("Nenhum lote foi identificado para os itens do orçamento.")
    arquivos, registros = [], []
    for grupo in grupos:
        lote = grupo.get("lote") or {}
        itens = grupo.get("itens") or []
        if not lote or not itens:
            continue
        dados_grupo = dict(dados)
        dados_grupo["lote"] = lote
        dados_grupo["itens"] = itens
        dados_grupo.pop("grupos_lotes", None)
        conteudo, nome, total = gerar_requisicao_material_construcao(dados_grupo)
        arquivos.append((nome, conteudo))
        registros.append({"lote": lote, "valor_total": total,
                          "fornecedor": dados_grupo.get("fornecedor") or lote.get("fornecedor", "")})
    if not arquivos:
        raise ValueError("Não há itens classificados para gerar as requisições.")
    pacote = BytesIO()
    with ZipFile(pacote, "w", ZIP_DEFLATED) as zip_file:
        for nome, conteudo in arquivos:
            zip_file.writestr(nome, conteudo)
    return pacote.getvalue(), "REQUISICOES_MATERIAIS_CONSTRUCAO.zip", registros


def gerar_requisicoes_pneus(conteudo_relacao: bytes, dados: dict) -> tuple[bytes, str, list[dict]]:
    catalogo = {item["numero"]: item for item in ler_relacao_pneus(conteudo_relacao)["itens"]}
    solicitados = dados.get("itens") or []
    if not solicitados:
        raise ValueError("Informe ao menos um item de pneu.")
    for campo, rotulo in (
        ("destino", "destino"), ("fonte_recurso", "fonte/recurso"),
        ("responsavel_nome", "responsável"), ("responsavel_cargo", "cargo do responsável"),
    ):
        if not _texto(dados.get(campo)):
            raise ValueError(f"Informe {rotulo}.")
    agrupados: dict[str, list[dict]] = {}
    numeros_processados: set[int] = set()
    for solicitado in solicitados:
        try:
            numero = int(solicitado.get("numero"))
            quantidade = float(solicitado.get("quantidade"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Número ou quantidade de item inválido.") from exc
        item = catalogo.get(numero)
        if numero in numeros_processados:
            raise ValueError(f"O item {numero} foi informado mais de uma vez.")
        numeros_processados.add(numero)
        if not item:
            raise ValueError(f"O item {numero} não existe na relação importada.")
        if quantidade <= 0 or quantidade > item["saldo_quantidade"]:
            raise ValueError(
                f"A quantidade do item {numero} deve estar entre 0 e o saldo {item['saldo_quantidade']:g}."
            )
        agrupados.setdefault(item["fornecedor"], []).append({**item, "quantidade": quantidade})

    if any(len(itens) > 20 for itens in agrupados.values()):
        raise ValueError("Cada fornecedor pode possuir no máximo 20 itens por requisição.")

    fornecedores = dados.get("fornecedores") or {}
    arquivos: list[tuple[str, bytes]] = []
    registros: list[dict] = []
    for fornecedor, itens in agrupados.items():
        workbook = load_workbook(MODELO_PNEU)
        ws = workbook.active
        detalhes = fornecedores.get(fornecedor, {})
        if not _texto(detalhes.get("endereco")) or not _texto(detalhes.get("cidade")):
            raise ValueError(f"Informe o endereço e a cidade do fornecedor {fornecedor}.")
        ws["B11"] = _texto_planilha(
            "Solicitamos que seja emitida Autorização de Fornecimento dos materiais/serviços "
            f"abaixo descritos destinados a: {_texto(dados.get('destino'))}"
        )
        ws["B13"] = f"Fornecedor: {_texto_planilha(fornecedor)}"
        ws["B15"] = f"Endereço: {_texto_planilha(detalhes.get('endereco'))}"
        ws["B17"] = f"Cidade: {_texto_planilha(detalhes.get('cidade'))}"
        ws["B19"] = f"Fonte/Recurso: {_texto_planilha(dados.get('fonte_recurso'))}"
        for linha in range(23, 43):
            for coluna in range(2, 9):
                ws.cell(linha, coluna).value = None
        total = 0.0
        for linha, item in enumerate(itens, 23):
            ws.cell(linha, 2).value = item["quantidade"]
            ws.cell(linha, 3).value = item["numero"]
            ws.cell(linha, 4).value = _texto_planilha(item["descricao"])
            ws.cell(linha, 5).value = item["valor_unitario"]
            ws.cell(linha, 6).value = 0
            ws.cell(linha, 7).value = f"=E{linha}-(E{linha}*F{linha})"
            ws.cell(linha, 8).value = f"=G{linha}*B{linha}"
            total += item["quantidade"] * item["valor_unitario"]
        ws["H43"] = "=SUM(H23:H42)"
        ws["B49"] = _texto_planilha(dados.get("local_data") or "MALLET-PR,")
        ws["D49"] = "=TODAY()"
        ws["D55"] = _texto_planilha(dados.get("responsavel_nome"))
        ws["D56"] = _texto_planilha(dados.get("responsavel_cargo"))
        ws["D57"] = _texto_planilha(dados.get("responsavel_ato"))
        saida = BytesIO()
        workbook.save(saida)
        nome_seguro = re.sub(r"[^A-Za-z0-9_-]+", "_", fornecedor).strip("_")[:60]
        arquivos.append((f"REQUISICAO_PNEUS_{nome_seguro}.xlsx", saida.getvalue()))
        registros.append({"fornecedor": fornecedor, "valor_total": round(total, 2)})

    pacote = BytesIO()
    with ZipFile(pacote, "w", ZIP_DEFLATED) as zip_file:
        for nome, conteudo in arquivos:
            zip_file.writestr(nome, conteudo)
    return pacote.getvalue(), "requisicoes_pneus.zip", registros


def ler_orcamento_excel(conteudo: bytes) -> dict:
    try:
        workbook = load_workbook(BytesIO(conteudo), data_only=True)
    except Exception as exc:
        raise ValueError("O orçamento deve ser uma planilha Excel .xlsx válida.") from exc

    melhor = None
    for planilha in workbook.worksheets:
        for linha in range(1, min(planilha.max_row, 100) + 1):
            cabecalhos = {_normalizar(planilha.cell(linha, coluna).value): coluna for coluna in range(1, planilha.max_column + 1)}
            descricao = next((c for h, c in cabecalhos.items() if any(x in h for x in ("descricao", "produto", "servico"))), None)
            if not descricao:
                descricao = next((c for h, c in cabecalhos.items() if h == "item"), None)
            quantidade = next((c for h, c in cabecalhos.items() if any(x in h for x in ("quantidade", "qtd", "qtde"))), None)
            unitario = next((c for h, c in cabecalhos.items() if "unit" in h or "preco" in h or "valor" in h), None)
            codigo = next((c for h, c in cabecalhos.items() if "codigo" in h or h in {"cod", "cód"}), None)
            if descricao and (quantidade or unitario):
                melhor = (planilha, linha, descricao, quantidade, unitario, codigo)
                break
        if melhor:
            break
    if not melhor:
        raise ValueError("Não encontrei colunas de descrição, quantidade e valor unitário no orçamento.")

    planilha, cabecalho, descricao, quantidade, unitario, codigo = melhor
    itens = []
    vazias = 0
    for linha in range(cabecalho + 1, planilha.max_row + 1):
        nome = _texto(planilha.cell(linha, descricao).value)
        if not nome:
            vazias += 1
            if vazias >= 5 and itens:
                break
            continue
        vazias = 0
        normalizado = _normalizar(nome)
        if normalizado.startswith("total") or normalizado in {"subtotal", "valor total"}:
            break
        qtd = _numero(planilha.cell(linha, quantidade).value, 1) if quantidade else 1
        valor = _numero(planilha.cell(linha, unitario).value) if unitario else 0
        if qtd > 0 and (valor > 0 or nome):
            itens.append({"codigo": _texto(planilha.cell(linha, codigo).value) if codigo else "",
                          "descricao": nome, "quantidade": qtd, "valor_unitario": valor})
    if not itens:
        raise ValueError("A planilha foi lida, mas nenhum item de orçamento foi encontrado.")
    if len(itens) > 29:
        raise ValueError("O modelo comporta até 29 itens por requisição.")
    return {"arquivo": planilha.title, "itens": itens, "total": sum(i["quantidade"] * i["valor_unitario"] for i in itens)}


def _achar_colunas(cabecalhos: list) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    nomes = [_normalizar(valor) for valor in cabecalhos]
    descricao = next((i for i, h in enumerate(nomes) if any(x in h for x in ("descricao", "produto", "servico", "especificacao"))), None)
    quantidade = next((i for i, h in enumerate(nomes) if any(x in h for x in ("quantidade", "qtd", "qtde", "quant."))), None)
    unitario = next((i for i, h in enumerate(nomes) if "unit" in h or "preco" in h), None)
    total = next((i for i, h in enumerate(nomes) if "total" in h), None)
    desconto = next((i for i, h in enumerate(nomes) if "% a/d" in h or "desconto" in h or h in {"a/d", "%ad"}), None)
    return descricao, quantidade, unitario, total, desconto


def _ler_dados_fornecedor_pdf(linhas: list[str]) -> dict[str, str]:
    """Lê tanto o cabeçalho antigo quanto o novo usado pela Iracenter."""
    linhas = [linha.strip() for linha in linhas if linha and linha.strip()]
    if not linhas:
        return {}

    limite_cliente = next(
        (i for i, linha in enumerate(linhas) if _normalizar(linha) == "cliente"),
        len(linhas),
    )
    cabecalho = linhas[:limite_cliente]
    indice_cnpj = next(
        (i for i, linha in enumerate(cabecalho) if "cnpj" in _normalizar(linha)),
        None,
    )

    fornecedor = ""
    if indice_cnpj is not None:
        # No modelo novo, o CNPJ está na linha de atividade e a razão social
        # fica imediatamente acima. No antigo, razão social e CNPJ dividem a linha.
        linha_cnpj = cabecalho[indice_cnpj]
        antes_cnpj = re.split(r"\bCNPJ\s*: ?", linha_cnpj, maxsplit=1, flags=re.I)[0].strip(" -|")
        if re.search(r"(?:LTDA|ME|EIRELI|S/?A)\b", antes_cnpj, re.I):
            fornecedor = antes_cnpj
        elif indice_cnpj:
            fornecedor = cabecalho[indice_cnpj - 1]

    if not fornecedor:
        fornecedor = cabecalho[0]

    endereco = next(
        (linha for linha in cabecalho if re.search(r"\b(?:rua|av(?:enida)?\.?|rodovia|estrada)\b", _normalizar(linha))),
        "",
    )
    return {"fornecedor": fornecedor, "endereco": endereco}


def _ler_itens_ocr_posicional(pagina) -> list[dict]:
    """Reconstrói tabelas de alguns PDFs escaneados cujo OCR separa cada letra."""
    palavras = pagina.extract_words(x_tolerance=1, y_tolerance=1) or []
    candidatos = [p for p in palavras if 35 < p["x0"] < 66 and 160 < p["top"] < pagina.height * .55
                  and _texto(p["text"]).isdigit()]
    grupos: list[dict] = []
    for palavra in candidatos:
        grupo = next((g for g in grupos if abs(palavra["top"] - g["y"]) < 4), None)
        if grupo is None:
            grupo = {"y": palavra["top"], "palavras": []}
            grupos.append(grupo)
        grupo["palavras"].append(palavra)
        grupo["y"] = sum(p["top"] for p in grupo["palavras"]) / len(grupo["palavras"])

    def faixa(x0: float, x1: float, y: float, espacada: bool = False) -> str:
        selecionadas = [p for p in palavras if x0 <= p["x0"] < x1
                        and abs((p["top"] - .019 * (p["x0"] - 40)) - y) < 3.8]
        selecionadas.sort(key=lambda p: p["x0"])
        partes, anterior = [], None
        for palavra in selecionadas:
            if espacada and anterior is not None and palavra["x0"] - anterior > 2:
                partes.append(" ")
            partes.append(_texto(palavra["text"]))
            anterior = palavra["x1"]
        return "".join(partes).strip()

    itens = []
    for grupo in sorted(grupos, key=lambda g: g["y"]):
        y = grupo["y"]
        codigo = faixa(35, 66, y)
        descricao = faixa(67, 305, y, True)
        quantidade_texto = faixa(338, 370, y)
        unitario_texto = faixa(382, 425, y)
        if not (codigo.isdigit() and descricao and quantidade_texto and unitario_texto):
            continue
        quantidade = _numero(quantidade_texto)
        # O OCR frequentemente perde a vírgula de duas casas da quantidade.
        if "," not in quantidade_texto and quantidade_texto.endswith("00") and quantidade >= 100:
            quantidade /= 100
        valor = _numero(unitario_texto)
        if quantidade > 0 and valor > 0:
            itens.append({"codigo": codigo, "descricao": descricao, "quantidade": quantidade,
                          "valor_unitario": valor, "desconto": 0, "tipo": "material"})
    return itens if len(itens) >= 2 else []


def ler_orcamento_pdf(conteudo: bytes) -> dict:
    try:
        pdf = pdfplumber.open(BytesIO(conteudo))
    except Exception as exc:
        raise ValueError("O arquivo não é um PDF válido.") from exc
    itens = []
    metadados = {}
    tipos_encontrados = set()
    tinha_texto = False
    with pdf:
        for pagina in pdf.pages:
            quantidade_antes = len(itens)
            texto_pagina = pagina.extract_text() or ""
            tinha_texto = tinha_texto or bool(texto_pagina.strip())
            linhas_texto = texto_pagina.splitlines()
            if not metadados.get("fornecedor") and linhas_texto:
                metadados.update(_ler_dados_fornecedor_pdf(linhas_texto))
            placa = re.search(r"PLACA:\s*([A-Z0-9-]+)", texto_pagina, re.I)
            orcamento = re.search(r"(?:N[°º]\s*)?OR[ÇC]AMENTO:\s*([\w/-]+)", texto_pagina, re.I)
            identificadores = []
            if placa:
                identificadores.append(f"PLACA- {placa.group(1)}")
                metadados["placa"] = placa.group(1)
            if orcamento:
                identificadores.append(f"ORÇAMENTO- {orcamento.group(1)}")
                metadados["numero_orcamento"] = orcamento.group(1)
            if identificadores:
                metadados["identificacao"] = "   ".join(identificadores)
            cidade = re.search(r"CEP[^\n]*?\s[-–]\s*([A-ZÀ-Ý ]+?)(?:-PR|/PR|\n)", texto_pagina, re.I)
            if cidade:
                metadados.setdefault("cidade", cidade.group(1).strip())
            for tabela in pagina.extract_tables() or []:
                colunas = None
                secao = ""
                for linha in tabela:
                    primeira = _normalizar(linha[0] if linha else "")
                    if "mao de obra" in primeira or "servico" in primeira:
                        secao = "servico"
                    elif "pecas" in primeira or "produtos" in primeira:
                        secao = "material"
                    achadas = _achar_colunas(linha or [])
                    if achadas[0] is not None and (achadas[1] is not None or achadas[2] is not None):
                        colunas = achadas
                        continue
                    if colunas is None:
                        continue
                    descricao, quantidade, unitario, total, desconto_coluna = colunas
                    if not linha or descricao >= len(linha):
                        continue
                    nome = _texto(linha[descricao]).replace("\n", " ")
                    nome_normalizado = _normalizar(nome)
                    if not nome or nome_normalizado.startswith(("total", "subtotal")):
                        continue
                    qtd = _numero(linha[quantidade], 1) if quantidade is not None and quantidade < len(linha) else 1
                    valor = _numero(linha[unitario]) if unitario is not None and unitario < len(linha) else 0
                    if not valor and total is not None and total < len(linha) and qtd:
                        valor = _numero(linha[total]) / qtd
                    if qtd > 0 and valor > 0:
                        desconto = _numero(linha[desconto_coluna]) if desconto_coluna is not None and desconto_coluna < len(linha) else 0
                        itens.append({"descricao": nome, "quantidade": qtd, "valor_unitario": round(valor, 2), "desconto": desconto, "tipo": secao or "material"})
                        tipos_encontrados.add(secao or "material")
            if len(itens) == quantidade_antes:
                itens_ocr = _ler_itens_ocr_posicional(pagina)
                itens.extend(itens_ocr)
                if itens_ocr:
                    tipos_encontrados.add("material")
    if not itens:
        if not tinha_texto:
            raise ValueError("Este PDF parece digitalizado como imagem. Envie um PDF com texto pesquisável ou aplique OCR antes de importar.")
        raise ValueError("Não encontrei no PDF uma tabela com descrição, quantidade e valor unitário.")
    if len(itens) > 29:
        raise ValueError("O modelo comporta até 29 itens por requisição.")
    tipo = "servico" if tipos_encontrados == {"servico"} else "material"
    grupos = {
        nome: {
            "itens": [item for item in itens if item["tipo"] == nome],
            "total": sum(item["quantidade"] * item["valor_unitario"] for item in itens if item["tipo"] == nome),
        }
        for nome in ("material", "servico") if any(item["tipo"] == nome for item in itens)
    }
    return {"arquivo": "PDF", "itens": itens, "total": sum(i["quantidade"] * i["valor_unitario"] for i in itens), "tipo": tipo, "misto": len(grupos) > 1, "grupos": grupos, "metadados": metadados}


def ler_orcamento(conteudo: bytes, nome_arquivo: str = "") -> dict:
    if nome_arquivo.lower().endswith(".pdf") or conteudo[:4] == b"%PDF":
        return ler_orcamento_pdf(conteudo)
    return ler_orcamento_excel(conteudo)


def gerar_requisicao(tipo: str, dados: dict) -> tuple[bytes, str]:
    if tipo not in MODELOS:
        raise ValueError("Tipo de requisição inválido.")
    itens = dados.get("itens") or []
    if not itens or len(itens) > 29:
        raise ValueError("Informe de 1 a 29 itens.")
    workbook = load_workbook(MODELOS[tipo])
    ws = workbook.active
    fornecedor = _texto(dados.get("fornecedor"))
    endereco = _texto(dados.get("endereco"))
    cidade = _texto(dados.get("cidade"))
    destino = _texto(dados.get("destino")) or "SEC. EDUCAÇÃO - SETOR TRANSPORTE"
    fonte = _texto(dados.get("fonte_recurso"))
    identificacao = _texto(dados.get("identificacao"))
    desconto = _numero(dados.get("desconto"))
    if desconto > 1:
        desconto /= 100

    ws["B11"] = f"Solicitamos que seja emitida Autorização de Fornecimento dos materiais/serviços abaixo descritos destinados a:      {destino}"
    ws["B13"] = f"Fornecedor: {fornecedor}"
    ws["B15"] = f"Endereço: {endereco}"
    ws["B17"] = f"Cidade: {cidade}"
    ws["B19"] = f"Fonte/Recurso: {fonte}                              {identificacao}"
    ws["E21"] = "R$ (Hora)" if tipo == "servico" else "R$ (Unitário)"
    for linha in range(23, 52):
        for coluna in (2, 4, 5, 6, 7, 8):
            ws.cell(linha, coluna).value = None
    for indice, item in enumerate(itens, 23):
        qtd = _numero(item.get("quantidade"), 1)
        valor = _numero(item.get("valor_unitario"))
        ws.cell(indice, 2).value = qtd
        ws.cell(indice, 4).value = _texto(item.get("descricao"))
        ws.cell(indice, 5).value = valor
        desconto_item = _numero(item.get("desconto"), desconto)
        if desconto_item > 1:
            desconto_item /= 100
        ws.cell(indice, 6).value = desconto_item
        ws.cell(indice, 7).value = f"=E{indice}-(E{indice}*F{indice})"
        ws.cell(indice, 8).value = f"=G{indice}*B{indice}"
    ws["H52"] = "=SUM(H23:H51)"
    saida = BytesIO()
    workbook.save(saida)
    placa = _texto(dados.get("placa"))
    numero_orcamento = _texto(dados.get("numero_orcamento"))
    if placa and numero_orcamento:
        categoria = "PEÇAS" if tipo == "material" else "SERVIÇO"
        nome_arquivo = f"{placa} {numero_orcamento} {categoria}.xlsx"
    else:
        nome = re.sub(r"[^A-Za-z0-9_-]+", "_", identificacao or tipo).strip("_")
        nome_arquivo = f"requisicao_{nome}.xlsx"
    return saida.getvalue(), nome_arquivo

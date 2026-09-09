from io import BytesIO
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from openpyxl import Workbook, load_workbook

from requisicao import (
    _ler_dados_fornecedor_pdf,
    _analisar_textos_relacao_pneus,
    gerar_requisicao,
    gerar_requisicoes_pneus,
    gerar_requisicao_impressoras,
    ler_demonstrativo_impressoras,
    ler_orcamento,
    ler_saldos_materiais_construcao,
    gerar_requisicao_material_construcao,
    gerar_requisicoes_material_construcao,
)


def test_le_cabecalho_novo_do_fornecedor():
    linhas = [
        "Rua Olimpio Odorico Silva, 160-SW - Vila Mariana - Mallet/PR - CEP 84570-000",
        "IRACENTER",
        "MARCELO AMARAL LUCAS LTDA",
        "PECAS E SERVICOS AUTOMOTIVOS CNPJ 34.843.253/0002-20",
        "Automoveis - Onibus - Caminhoes - Maquinas Pesadas",
        "CLIENTE",
        "MUNICIPIO DE MALLET",
        "CNPJ: 75.654.566/0001-36",
        "RUA: MAJOR ESTEVAO, 180",
    ]
    assert _ler_dados_fornecedor_pdf(linhas) == {
        "fornecedor": "MARCELO AMARAL LUCAS LTDA",
        "endereco": linhas[0],
    }


def _orcamento() -> bytes:
    workbook = Workbook()
    planilha = workbook.active
    planilha.append(["ITEM", "DESCRIÇÃO", "QTD", "VALOR UNITÁRIO"])
    planilha.append([1, "Filtro de óleo", 2, 35.5])
    planilha.append([2, "Correia", 1, 90])
    arquivo = BytesIO()
    workbook.save(arquivo)
    return arquivo.getvalue()


def test_le_orcamento_por_cabecalhos():
    resultado = ler_orcamento(_orcamento())
    assert resultado["itens"][0] == {
        "descricao": "Filtro de óleo",
        "quantidade": 2.0,
        "valor_unitario": 35.5,
    }
    assert resultado["total"] == 161


def test_gera_requisicao_com_formulas_e_desconto():
    itens = ler_orcamento(_orcamento())["itens"]
    conteudo, nome = gerar_requisicao(
        "material",
        {
            "fornecedor": "Fornecedor Teste",
            "endereco": "Rua A",
            "cidade": "Mallet",
            "fonte_recurso": "1000",
            "identificacao": "ORDEM 1/2026",
            "desconto": 15,
            "itens": itens,
        },
    )
    planilha = load_workbook(BytesIO(conteudo), data_only=False).active
    assert nome == "requisicao_ORDEM_1_2026.xlsx"
    assert planilha["D23"].value == "Filtro de óleo"
    assert planilha["F23"].value == 0.15
    assert planilha["H23"].value == "=G23*B23"
    assert planilha["H52"].value == "=SUM(H23:H51)"


class TestRequisicaoPneus(unittest.TestCase):
    def test_le_item_fornecedor_preco_e_saldo(self):
        texto = """Contratação: 70/2025 Data contratação: 05/05/2025 Fornecedor: BENICIO PNEUS LTDA
PNEUS NOVOS 205/70X15, 08 LONAS, RADIAL
22 370,000 370,000 18,000 0,000 10,000 8,000 6.660,00 0,00 3.700,00 2.960,00
PARA VEÍCULOS DA FROTA MUNICIPAL
"""
        itens = _analisar_textos_relacao_pneus([texto])
        self.assertEqual(len(itens), 1)
        self.assertEqual(itens[0]["numero"], 22)
        self.assertEqual(itens[0]["fornecedor"], "BENICIO PNEUS LTDA")
        self.assertEqual(itens[0]["valor_unitario"], 370)
        self.assertEqual(itens[0]["saldo_quantidade"], 8)
        self.assertIn("FROTA MUNICIPAL", itens[0]["descricao"])

    def test_separa_arquivos_por_fornecedor_no_zip(self):
        catalogo = {"itens": [
            {"numero": 1, "descricao": "Pneu A", "fornecedor": "Fornecedor A", "contratacao": "1/2025", "valor_unitario": 100, "saldo_quantidade": 4},
            {"numero": 2, "descricao": "Pneu B", "fornecedor": "Fornecedor B", "contratacao": "2/2025", "valor_unitario": 200, "saldo_quantidade": 3},
        ]}
        dados = {
            "itens": [{"numero": 1, "quantidade": 2}, {"numero": 2, "quantidade": 1}],
            "fornecedores": {
                "Fornecedor A": {"endereco": "Rua A", "cidade": "Mallet"},
                "Fornecedor B": {"endereco": "Rua B", "cidade": "Mallet"},
            },
            "destino": "Secretaria", "fonte_recurso": "1000",
            "responsavel_nome": "Responsável", "responsavel_cargo": "Cargo",
        }
        with patch("requisicao.ler_relacao_pneus", return_value=catalogo):
            conteudo, nome, registros = gerar_requisicoes_pneus(b"pdf", dados)
        self.assertEqual(nome, "requisicoes_pneus.zip")
        self.assertEqual(len(registros), 2)
        with ZipFile(BytesIO(conteudo)) as pacote:
            self.assertEqual(len(pacote.namelist()), 2)

    def test_impede_quantidade_superior_ao_saldo(self):
        catalogo = {"itens": [
            {"numero": 8, "descricao": "Pneu", "fornecedor": "Fornecedor", "contratacao": "1/2025", "valor_unitario": 300, "saldo_quantidade": 2},
        ]}
        dados = {
            "itens": [{"numero": 8, "quantidade": 3}],
            "destino": "Secretaria", "fonte_recurso": "1000",
            "responsavel_nome": "Responsável", "responsavel_cargo": "Cargo",
        }
        with patch("requisicao.ler_relacao_pneus", return_value=catalogo):
            with self.assertRaisesRegex(ValueError, "saldo 2"):
                gerar_requisicoes_pneus(b"pdf", dados)


class TestRequisicaoImpressoras(unittest.TestCase):
    def test_agrupa_producao_por_secretaria_categoria_e_tarifa(self):
        tabela = [
            ["Serial", "Secretaria", "Local", "Modelo", "Inicial", "Final", "Produção", "Total", "Tipo", "Setor"],
            ["A", "EDUCACAO", "ESCOLA 1", "M432", "1", "101", "100", "R$ 9,00", "PAGINA PB R$ 0,09", ""],
            ["B", "EDUCACAO", "ESCOLA 2", "M432", "2", "202", "200", "R$ 18,00", "PAGINA PB R$ 0,09", ""],
            ["C", "EDUCACAO", "ESCOLA 3", "M408", "3", "53", "50", "R$ 4,00", "PAGINA PB R$ 0,08", ""],
        ]
        pagina = unittest.mock.MagicMock()
        pagina.extract_tables.return_value = [tabela]
        pdf = unittest.mock.MagicMock()
        pdf.pages = [pagina]
        pdf.__enter__.return_value = pdf
        with patch("requisicao.pdfplumber.open", return_value=pdf):
            resultado = ler_demonstrativo_impressoras(b"%PDF")
        grupos = sorted(resultado["grupos"], key=lambda item: item["valor_unitario"])
        self.assertEqual([(g["producao"], g["valor_unitario"], g["total"]) for g in grupos],
                         [(50, .08, 4), (300, .09, 27)])

    def test_gera_planilha_separada_com_formulas(self):
        demonstrativo = {"grupos": [
            {"secretaria": "Educação", "categoria": "pb", "valor_unitario": .09,
             "producao": 300, "total": 27},
            {"secretaria": "Educação", "categoria": "pb", "valor_unitario": .08,
             "producao": 50, "total": 4},
        ]}
        with patch("requisicao.ler_demonstrativo_impressoras", return_value=demonstrativo):
            conteudo, nome, total = gerar_requisicao_impressoras(
                b"pdf", {"secretaria": "Educação", "contrato": "187/23", "fonte_recurso": "1000"}
            )
        ws = load_workbook(BytesIO(conteudo), data_only=False).active
        self.assertIn("PB", nome)
        self.assertEqual(total, 31)
        self.assertEqual(ws["C24"].value, 300)
        self.assertEqual(ws["D25"].value, .08)
        self.assertEqual(ws["E24"].value, "=C24*D24")


class TestMateriaisConstrucao(unittest.TestCase):
    def test_le_lote_e_saldo_financeiro(self):
        texto = """Contratação: 150/2023 Data contratação: 30/10/2023 Fornecedor: FORNECEDOR LTDA
Processo administrativo: 124/2023 Data processo: 25/08/2023
12 MATERIAIS HIDRÁULICOS. 194.250,000 194.250,000 1,000 1,000 1,133 0,867 194.250,00 194.250,00 220.150,37 168.349,63
"""
        pagina = unittest.mock.MagicMock()
        pagina.extract_text.return_value = texto
        pdf = unittest.mock.MagicMock()
        pdf.pages = [pagina]
        pdf.__enter__.return_value = pdf
        with patch("requisicao.pdfplumber.open", return_value=pdf):
            resultado = ler_saldos_materiais_construcao(b"%PDF")
        lote = resultado["lotes"][0]
        self.assertEqual(lote["numero"], 12)
        self.assertEqual(lote["contrato"], "150/2023")
        self.assertEqual(lote["saldo_valor"], 168349.63)

    def test_gera_modelo_e_impede_ultrapassar_saldo(self):
        dados = {
            "fornecedor": "Fornecedor", "endereco": "Rua A", "cidade": "Mallet",
            "destino": "Secretaria", "fonte_recurso": "1103", "desconto": 10,
            "lote": {"numero": 12, "descricao": "MATERIAIS HIDRÁULICOS.",
                     "contrato": "150/2023", "saldo_valor": 100},
            "itens": [{"codigo": "123", "descricao": "Tubo", "quantidade": 2,
                       "valor_unitario": 40}],
        }
        conteudo, nome, total = gerar_requisicao_material_construcao(dados)
        ws = load_workbook(BytesIO(conteudo), data_only=False).active
        self.assertEqual(total, 72)
        self.assertEqual(ws["C25"].value, "123")
        self.assertEqual(ws["H25"].value, "=F25-(F25*G25)")
        dados["itens"][0]["quantidade"] = 3
        with self.assertRaisesRegex(ValueError, "ultrapassa o saldo"):
            gerar_requisicao_material_construcao(dados)

    def test_gera_zip_separado_por_lote(self):
        dados = {
            "fornecedor": "Fornecedor", "endereco": "Rua A", "cidade": "Mallet",
            "destino": "Secretaria", "fonte_recurso": "1103", "desconto": 0,
            "grupos_lotes": [
                {"lote": {"numero": 3, "descricao": "MATERIAIS DE PINTURA",
                           "contrato": "150/2023", "saldo_valor": 1000},
                 "itens": [{"descricao": "Tinta", "quantidade": 1, "valor_unitario": 100}]},
                {"lote": {"numero": 13, "descricao": "MATERIAIS ELÉTRICOS",
                           "contrato": "150/2023", "saldo_valor": 1000},
                 "itens": [{"descricao": "Lâmpada", "quantidade": 2, "valor_unitario": 20}]},
            ],
        }
        conteudo, nome, registros = gerar_requisicoes_material_construcao(dados)
        self.assertEqual(nome, "REQUISICOES_MATERIAIS_CONSTRUCAO.zip")
        self.assertEqual([r["valor_total"] for r in registros], [100, 40])
        with ZipFile(BytesIO(conteudo)) as pacote:
            self.assertEqual(len(pacote.namelist()), 2)

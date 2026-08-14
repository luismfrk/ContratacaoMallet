from __future__ import annotations

from decimal import Decimal
from typing import Any

TIPOS_TR = {
    "compras": {"titulo": "Compras", "exige_fornecedor": False, "exige_itens": True},
    "servicos": {"titulo": "Serviços", "exige_fornecedor": False, "exige_itens": True},
    "credenciamento": {
        "titulo": "Credenciamento",
        "exige_fornecedor": False,
        "exige_itens": True,
    },
    "obras_engenharia": {
        "titulo": "Obras e Serviços de Engenharia",
        "exige_fornecedor": False,
        "exige_itens": False,
    },
    "servicos_pessoa_fisica": {
        "titulo": "Serviços – Pessoa Física",
        "exige_fornecedor": True,
        "exige_itens": True,
    },
    "compras_dispensa_inexigibilidade": {
        "titulo": "Compras – Dispensa/Inexigibilidade",
        "exige_fornecedor": True,
        "exige_itens": True,
    },
    "servicos_dispensa_inexigibilidade": {
        "titulo": "Serviços – Dispensa/Inexigibilidade",
        "exige_fornecedor": True,
        "exige_itens": True,
    },
}


def texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def listar_tipos_tr() -> list[dict[str, Any]]:
    return [{"id": chave, **valor} for chave, valor in TIPOS_TR.items()]


def validar_tr(tipo: str, dados: dict[str, Any]) -> None:
    configuracao = TIPOS_TR.get(tipo)
    if not configuracao:
        raise ValueError("Tipo de Termo de Referência inválido.")
    campos = {
        "secretaria": "Secretaria",
        "objeto": "Objeto",
        "fundamentacao": "Fundamentação",
        "metodologia_calculo": "Metodologia de cálculo",
        "vigencia_meses": "Prazo de vigência",
        "criterio_selecao": "Critério de seleção",
        "requisitos": "Requisitos",
        "obrigacoes": "Obrigações da contratada",
        "recebimento": "Recebimento",
        "pagamento": "Condições de pagamento",
        "reajuste": "Reajuste",
        "fiscal_nome": "Fiscal",
        "fiscal_portaria": "Portaria do fiscal",
        "subcontratacao": "Subcontratação",
        "previsao_orcamentaria": "Previsão orçamentária",
        "dotacoes": "Dotações orçamentárias",
        "anexos": "Anexos",
        "responsavel_nome": "Responsável pela elaboração",
        "autoridade_nome": "Autoridade signatária",
        "autoridade_cargo": "Cargo da autoridade",
    }
    if configuracao["exige_fornecedor"]:
        campos.update(
            {
                "fornecedor_nome": "Fornecedor escolhido",
                "fornecedor_documento": "CNPJ/CPF do fornecedor",
                "razoes_escolha": "Razões da escolha",
            }
        )
    ausentes = [rotulo for campo, rotulo in campos.items() if not texto(dados.get(campo))]
    if ausentes:
        raise ValueError(
            "Preencha os campos obrigatórios: " + ", ".join(ausentes) + "."
        )
    try:
        if int(dados["vigencia_meses"]) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O prazo de vigência deve ser maior que zero.") from exc

    itens = dados.get("itens", [])
    if configuracao["exige_itens"] and (not isinstance(itens, list) or not itens):
        raise ValueError("Adicione pelo menos um item ao Termo de Referência.")
    for indice, item in enumerate(itens, start=1):
        if not texto(item.get("descricao")):
            raise ValueError(f"Informe a descrição do item {indice}.")
        try:
            if Decimal(str(item.get("quantidade"))) <= 0:
                raise ValueError
            if Decimal(str(item.get("valor_unitario"))) < 0:
                raise ValueError
        except Exception as exc:
            raise ValueError(f"Revise a quantidade e o valor do item {indice}.") from exc


def gerar_tr(tipo: str, dados: dict[str, Any]) -> dict[str, Any]:
    validar_tr(tipo, dados)
    config = TIPOS_TR[tipo]
    secoes = (
        ("FUNDAMENTAÇÃO", "fundamentacao"),
        ("OBJETO", "objeto"),
        ("METODOLOGIA DE CÁLCULO", "metodologia_calculo"),
        ("CRITÉRIO DE SELEÇÃO", "criterio_selecao"),
        ("REQUISITOS", "requisitos"),
        ("OBRIGAÇÕES", "obrigacoes"),
        ("RECEBIMENTO", "recebimento"),
        ("PAGAMENTO", "pagamento"),
        ("REAJUSTE", "reajuste"),
        ("SUBCONTRATAÇÃO", "subcontratacao"),
        ("PREVISÃO ORÇAMENTÁRIA", "previsao_orcamentaria"),
        ("ANEXOS", "anexos"),
    )
    linhas = [f"TERMO DE REFERÊNCIA – {config['titulo'].upper()}", ""]
    for titulo, campo in secoes:
        linhas.extend([titulo, texto(dados[campo]), ""])
    return {
        "titulo": f"TR – {config['titulo']}",
        "conteudo": "\n".join(linhas),
        "modo": "modelo oficial estruturado",
    }

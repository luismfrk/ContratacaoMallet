from __future__ import annotations

from decimal import Decimal
from typing import Any


def texto(valor: Any) -> str:
    return "" if valor is None else str(valor).strip()


def validar_etp_obras(dados: dict[str, Any]) -> None:
    campos = {
        "objeto": "Objeto",
        "solicitante": "Solicitante",
        "responsavel_nome": "Responsável pela elaboração",
        "justificativa": "Justificativa",
        "resultados_pretendidos": "Resultados pretendidos",
        "alternativas": "Alternativas",
        "solucao_escolhida": "Solução escolhida",
        "local_execucao": "Local de execução",
        "servicos_materiais": "Serviços e materiais",
        "metodologia_executiva": "Metodologia executiva",
        "cronograma": "Cronograma",
        "estimativa_quantidades": "Estimativa de quantidades",
        "fontes_pesquisa": "Fontes da pesquisa",
        "metodologia_pesquisa": "Metodologia da pesquisa",
        "justificativa_solucao": "Justificativa da solução",
        "custos_operacionais": "Custos operacionais futuros",
        "interferencias": "Levantamento de interferências",
        "titularidade_area": "Titularidade da área",
        "valor_estimado": "Valor estimado",
        "previsao_planos": "Previsão no PPA e PCA",
        "parcelamento": "Parcelamento",
        "contratacoes_correlatas": "Contratações correlatas",
        "capacitacao": "Capacitação",
        "impactos_ambientais": "Impactos ambientais",
        "declaracao_viabilidade": "Declaração de viabilidade",
        "anexos": "Anexos",
        "autoridade_nome": "Autoridade signatária",
        "autoridade_cargo": "Cargo da autoridade",
    }
    ausentes = [rotulo for campo, rotulo in campos.items() if not texto(dados.get(campo))]
    if ausentes:
        raise ValueError(
            "Preencha os campos obrigatórios: " + ", ".join(ausentes) + "."
        )
    try:
        if Decimal(str(dados["valor_estimado"])) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O valor estimado deve ser maior que zero.") from exc


def gerar_etp_obras(dados: dict[str, Any]) -> dict[str, Any]:
    validar_etp_obras(dados)
    pares = (
        ("NECESSIDADE", "justificativa"),
        ("RESULTADOS PRETENDIDOS", "resultados_pretendidos"),
        ("ALTERNATIVAS", "alternativas"),
        ("SOLUÇÃO VIÁVEL", "solucao_escolhida"),
        ("LOCAL DE EXECUÇÃO", "local_execucao"),
        ("SERVIÇOS E MATERIAIS", "servicos_materiais"),
        ("METODOLOGIA EXECUTIVA", "metodologia_executiva"),
        ("CRONOGRAMA", "cronograma"),
        ("QUANTIDADES", "estimativa_quantidades"),
        ("CUSTOS OPERACIONAIS FUTUROS", "custos_operacionais"),
        ("INTERFERÊNCIAS", "interferencias"),
        ("TITULARIDADE DA ÁREA", "titularidade_area"),
        ("VIABILIDADE", "declaracao_viabilidade"),
    )
    linhas = ["ESTUDO TÉCNICO PRELIMINAR – OBRAS E SERVIÇOS DE ENGENHARIA", ""]
    for titulo, campo in pares:
        linhas.extend([titulo, texto(dados[campo]), ""])
    return {
        "titulo": "ETP – Obras e Serviços de Engenharia",
        "conteudo": "\n".join(linhas),
        "modo": "modelo oficial estruturado",
    }

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def validar_etp(dados: dict[str, Any]) -> None:
    obrigatorios = {
        "objeto": "Objeto",
        "solicitante": "Solicitante",
        "responsavel_nome": "Responsável pela elaboração",
        "justificativa": "Justificativa da necessidade",
        "resultados_pretendidos": "Resultados pretendidos",
        "alternativas": "Alternativas analisadas",
        "solucao_escolhida": "Solução escolhida",
        "requisitos": "Requisitos da contratação",
        "prazo_meses": "Prazo do contrato",
        "memoria_calculo": "Memória de cálculo",
        "fontes_pesquisa": "Fontes da pesquisa de preços",
        "metodologia_pesquisa": "Metodologia da pesquisa",
        "justificativa_solucao": "Justificativa da solução",
        "valor_estimado": "Valor estimado",
        "previsao_planos": "Previsão no PPA e PCA",
        "parcelamento": "Justificativa de parcelamento",
        "contratacoes_correlatas": "Contratações correlatas",
        "capacitacao": "Capacitação dos servidores",
        "impactos_ambientais": "Impactos ambientais",
        "declaracao_viabilidade": "Declaração de viabilidade",
        "autoridade_nome": "Autoridade signatária",
        "autoridade_cargo": "Cargo da autoridade",
    }
    ausentes = [
        rotulo for campo, rotulo in obrigatorios.items() if not _texto(dados.get(campo))
    ]
    if ausentes:
        raise ValueError(
            "Preencha os campos obrigatórios: " + ", ".join(ausentes) + "."
        )

    try:
        if int(dados["prazo_meses"]) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O prazo do contrato deve ser maior que zero.") from exc

    try:
        if Decimal(str(dados["valor_estimado"])) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O valor estimado deve ser maior que zero.") from exc

    itens = dados.get("itens")
    if not isinstance(itens, list) or not itens:
        raise ValueError("Adicione pelo menos um item à estimativa de quantidades.")
    for indice, item in enumerate(itens, start=1):
        if not _texto(item.get("descricao")) or not _texto(item.get("quantidade")):
            raise ValueError(f"Preencha a descrição e a quantidade do item {indice}.")


def gerar_etp(dados: dict[str, Any]) -> dict[str, Any]:
    validar_etp(dados)
    secoes = [
        ("1. INFORMAÇÕES BÁSICAS", _texto(dados["objeto"])),
        ("2. JUSTIFICATIVA DA NECESSIDADE", _texto(dados["justificativa"])),
        ("3. RESULTADOS PRETENDIDOS", _texto(dados["resultados_pretendidos"])),
        ("4. ANÁLISE DAS ALTERNATIVAS", _texto(dados["alternativas"])),
        ("SOLUÇÃO VIÁVEL", _texto(dados["solucao_escolhida"])),
        ("5. REQUISITOS DA CONTRATAÇÃO", _texto(dados["requisitos"])),
        ("6. ESTIMATIVA DAS QUANTIDADES", _texto(dados["memoria_calculo"])),
        ("7. PESQUISA DE PREÇOS", _texto(dados["fontes_pesquisa"])),
        ("8. JUSTIFICATIVA DA SOLUÇÃO", _texto(dados["justificativa_solucao"])),
        ("11. PARCELAMENTO", _texto(dados["parcelamento"])),
        ("12. CONTRATAÇÕES CORRELATAS", _texto(dados["contratacoes_correlatas"])),
        ("13. CAPACITAÇÃO", _texto(dados["capacitacao"])),
        ("14. IMPACTOS AMBIENTAIS", _texto(dados["impactos_ambientais"])),
        ("17. VIABILIDADE", _texto(dados["declaracao_viabilidade"])),
    ]
    conteudo = ["ESTUDO TÉCNICO PRELIMINAR – COMPRAS E SERVIÇOS", ""]
    for titulo, texto in secoes:
        conteudo.extend([titulo, texto, ""])
    return {
        "titulo": "ETP – Compras e Serviços",
        "conteudo": "\n".join(conteudo),
        "modo": "modelo oficial estruturado",
        "data": date.today().isoformat(),
    }

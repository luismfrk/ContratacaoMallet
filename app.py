from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class TipoDFD:
    titulo: str
    anexo: str
    abertura: str
    exige_contratada: bool = False


TIPOS_DFD: dict[str, TipoDFD] = {
    "pregao": TipoDFD("PREGÃO", "Anexo I", "processo de licitação"),
    "concorrencia": TipoDFD("CONCORRÊNCIA", "Anexo II", "processo de licitação"),
    "dispensa": TipoDFD(
        "DISPENSA DE LICITAÇÃO",
        "Anexo III",
        "processo administrativo de dispensa de licitação",
        True,
    ),
    "inexigibilidade": TipoDFD(
        "INEXIGIBILIDADE DE LICITAÇÃO",
        "Anexo IV",
        "processo administrativo de inexigibilidade de licitação",
        True,
    ),
    "credenciamento": TipoDFD(
        "CREDENCIAMENTO", "Anexo XV", "processo de credenciamento"
    ),
    "adesao": TipoDFD(
        "ADESÃO À ATA DE REGISTRO DE PREÇOS",
        "Anexo XVI",
        "processo de adesão à ata de registro de preços",
        True,
    ),
}


def listar_tipos_dfd() -> list[dict[str, Any]]:
    return [
        {
            "id": identificador,
            "titulo": configuracao.titulo,
            "anexo": configuracao.anexo,
            "exige_contratada": configuracao.exige_contratada,
        }
        for identificador, configuracao in TIPOS_DFD.items()
    ]


def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _valor_em_reais(valor: Any) -> str:
    numero = Decimal(str(valor))
    formatado = f"{numero:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")


def validar_dfd(tipo: str, dados: dict[str, Any]) -> None:
    configuracao = TIPOS_DFD.get(tipo)
    if not configuracao:
        raise ValueError("Tipo de DFD inválido.")

    obrigatorios = {
        "unidade_requisitante": "Unidade requisitante",
        "objeto": "Objeto",
        "justificativa": "Justificativa da necessidade",
        "quantitativo": "Quantitativo",
        "unidade_medida": "Unidade de medida",
        "valor_estimado": "Valor estimado",
        "fonte_estimativa": "Fonte da estimativa",
        "prazo_vigencia_meses": "Prazo de vigência",
        "data_pretendida": "Data pretendida",
        "responsavel_nome": "Nome do responsável",
        "responsavel_cargo": "Cargo do responsável",
        "responsavel_matricula": "Matrícula do responsável",
        "autoridade_nome": "Nome da autoridade signatária",
        "autoridade_cargo": "Cargo da autoridade signatária",
        "fundamento": "Fundamento",
    }
    if configuracao.exige_contratada:
        obrigatorios.update(
            {
                "contratada_nome": "Nome da contratada",
                "contratada_documento": "CNPJ/CPF da contratada",
            }
        )

    ausentes = [
        rotulo for campo, rotulo in obrigatorios.items() if not _texto(dados.get(campo))
    ]
    if ausentes:
        raise ValueError(
            "Preencha os campos obrigatórios: " + ", ".join(ausentes) + "."
        )

    try:
        if Decimal(str(dados["quantitativo"])) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O quantitativo deve ser maior que zero.") from exc

    try:
        if Decimal(str(dados["valor_estimado"])) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError("O valor estimado deve ser maior que zero.") from exc

    try:
        if int(dados["prazo_vigencia_meses"]) <= 0:
            raise ValueError
    except Exception as exc:
        raise ValueError(
            "O prazo de vigência deve ser um número inteiro maior que zero."
        ) from exc

    try:
        date.fromisoformat(_texto(dados["data_pretendida"]))
    except ValueError as exc:
        raise ValueError("Informe uma data pretendida válida.") from exc


def gerar_dfd(tipo: str, dados: dict[str, Any]) -> dict[str, Any]:
    validar_dfd(tipo, dados)
    configuracao = TIPOS_DFD[tipo]
    data_pretendida = date.fromisoformat(_texto(dados["data_pretendida"]))
    prazo = int(dados["prazo_vigencia_meses"])

    linhas = [
        f"Portaria nº 033/2026 – {configuracao.anexo}",
        "",
        f"DOCUMENTO DE FORMALIZAÇÃO DE DEMANDA – {configuracao.titulo}",
        "",
        "Sr. Prefeito Municipal",
        "",
        (
            "No uso das atribuições de meu cargo, venho respeitosamente solicitar "
            f"que seja dado início ao {configuracao.abertura}, com as características "
            "abaixo listadas, conforme as justificativas e os documentos anexos."
        ),
        "",
        f"IDENTIFICAÇÃO DA UNIDADE REQUISITANTE: {_texto(dados['unidade_requisitante'])}",
        "",
        f"OBJETO: {_texto(dados['objeto'])}",
        "",
        "JUSTIFICATIVA DA NECESSIDADE DA CONTRATAÇÃO:",
        _texto(dados["justificativa"]),
        "",
        f"QUANTITATIVO: {_texto(dados['quantitativo'])} {_texto(dados['unidade_medida'])}",
        "",
        f"VALOR INICIAL: {_valor_em_reais(dados['valor_estimado'])}",
        f"FONTE DA ESTIMATIVA: {_texto(dados['fonte_estimativa'])}",
        "",
        f"PRAZO DE VIGÊNCIA DO CONTRATO: {prazo} meses.",
        f"DATA PRETENDIDA DA CONTRATAÇÃO: {data_pretendida.strftime('%d/%m/%Y')}",
    ]

    if configuracao.exige_contratada:
        linhas.extend(
            [
                "",
                (
                    f"CONTRATADA: {_texto(dados['contratada_nome'])} "
                    f"({_texto(dados['contratada_documento'])})"
                ),
            ]
        )

    linhas.extend(
        [
            "",
            (
                "RESPONSÁVEL PELA SOLICITAÇÃO: "
                f"{_texto(dados['responsavel_nome'])}, "
                f"{_texto(dados['responsavel_cargo'])}, matrícula "
                f"{_texto(dados['responsavel_matricula'])}"
            ),
            f"CÓDIGO PNCP: {_texto(dados.get('codigo_pncp')) or 'Não informado'}",
            f"FUNDAMENTO: {_texto(dados['fundamento'])}",
            f"MODALIDADE: {configuracao.titulo}",
            "",
            f"{_texto(dados['autoridade_nome'])}",
            f"{_texto(dados['autoridade_cargo'])}",
        ]
    )

    return {
        "titulo": f"DFD – {configuracao.titulo}",
        "conteudo": "\n".join(linhas),
        "tipo": tipo,
        "modo": "modelo oficial estruturado",
    }

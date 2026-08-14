# Arquitetura proposta para a assistência por IA

## Posição no fluxo

```text
Formulário
   |
   v
Validação estrutural ----> Serviço de assistência por IA
   |                              |
   |                       sugestão revisável
   |                              |
   <-------- aceite do usuário ---+
   |
   v
Gerador determinístico de DFD/ETP/TR
   |
   v
Arquivo DOCX oficial
```

A IA não deve editar diretamente os modelos oficiais nem gerar o arquivo final.
Ela auxilia a redação de campos variáveis. A geração do DOCX continua sendo feita
pelos módulos determinísticos e testados do sistema.

## Componentes futuros

- `ai/service.py`: interface única usada pelo backend.
- `ai/providers/`: adaptadores para API externa ou modelo local.
- `ai/prompts/`: instruções versionadas por documento e campo.
- `POST /api/ai/suggest`: gera uma sugestão para um campo.
- `POST /api/ai/review`: aponta omissões e inconsistências sem alterar o texto.
- botões **Sugerir com IA** e **Revisar com IA** na interface.

## Regras de segurança

1. A chave da API fica somente em variável de ambiente no servidor.
2. O navegador nunca recebe nem armazena a chave.
3. Apenas os campos necessários são enviados ao modelo.
4. CPF, CNPJ e nomes de fornecedores devem ser removidos quando não forem
   necessários para a sugestão.
5. Toda sugestão deve ser aceita ou descartada por uma pessoa.
6. Cláusulas fixas e fundamentos legais não são substituídos automaticamente.
7. O sistema registra o texto original, a sugestão, o aceite, o modelo utilizado
   e a data da operação.
8. O arquivo final deve indicar internamente quais campos receberam assistência.

## Opções de implantação

### API externa

Mais simples para o projeto-piloto e geralmente produz textos melhores. Exige
análise contratual, política de dados e aprovação do setor de TI.

### Modelo local

Executado em equipamento ou servidor da prefeitura. Oferece maior controle dos
dados, mas exige hardware, manutenção, monitoramento e avaliação de qualidade.

O restante do sistema usa a mesma interface em ambas as opções. Assim, o
provedor pode ser trocado por configuração, sem alterar DFD, ETP, TR ou DOCX.

## Primeiras funções recomendadas

1. Melhorar a justificativa da necessidade sem inventar fatos.
2. Comparar alternativas no ETP.
3. Sugerir resultados pretendidos mensuráveis.
4. Revisar coerência entre objeto, quantidade, valor e prazo.
5. Identificar campos incompletos antes da geração do Word.

Não é recomendável começar com geração integral do documento ou parecer de
legalidade.

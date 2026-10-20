# Validação da entrega

Ambiente: Python 3.14.8 e PostgreSQL 17.11 no Windows.

- Bibliotecas instaladas no ambiente virtual; pip check sem dependências quebradas.
- A suíte verifica leitura, totais, classificação, arquivos inválidos, FITID obrigatório, persistência, duplicação, rollback e interface.
- Os testes de banco e interface usam esquemas isolados e preservam os dados locais.
- O exemplo público foi criado exclusivamente para demonstração: banco 000, agência 0000, conta CONTA-FICTICIA e três transações fictícias.
- Totais sintéticos: entradas de R$ 1.000,00, saídas de R$ 250,00 e saldo calculado de R$ 750,00.
- Saldo informado sintético de R$ 800,00 permite verificar o aviso de diferença de R$ 50,00.
- O usuário também conferiu o arquivo da atividade no DBeaver. Esse arquivo e as credenciais ficam somente no computador local.

Consulte README.md para reproduzir a validação.

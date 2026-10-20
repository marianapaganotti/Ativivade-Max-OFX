# Max-OFX — Integração de Dados

Aplicação acadêmica que recebe extratos OFX por upload, classifica as movimentações por regras e grava os resultados em PostgreSQL. Desenvolvida para a atividade de Integração de Dados da UNIFEOB.

Referência: https://maxvallim.github.io/UNIFEOB_IntegracaoDados/OFX/Desafio_OFX.html

## Funcionalidades

- Upload de arquivos OFX de até 10 MB e prévia antes da gravação.
- Data, descrição, valor, tipo, conta, categoria e regra aplicada por movimentação.
- Contagem de movimentações, entradas, saídas e saldo calculado.
- PostgreSQL real, usando psycopg2 e consultas parametrizadas.
- Classificação automática por palavras-chave com normalização de acentos e letras.
- Detecção de duplicatas por banco, agência, conta e FITID, inclusive entre arquivos diferentes.
- Rejeição de FITID existente com dados diferentes, com rollback de toda a importação.
- Histórico com filtros, gráfico de despesas por categoria e exportação CSV.
- Registro de arquivo importado com hash SHA-256.
- Leitura das contas bancárias presentes no OFX.

## Executar neste computador

Abra `iniciar.bat` com dois cliques, ou execute na pasta do projeto:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\iniciar.ps1
```

Acesse **http://127.0.0.1:8501**. A instância PostgreSQL portátil usa `127.0.0.1:55432` e banco `projeto_ofx`. Não há necessidade de instalar um serviço do Windows.

Para uma demonstração, clique em **Usar extrato de exemplo** e em **Classificar e salvar no PostgreSQL**. Você também pode selecionar seu próprio arquivo pelo upload. Em **Movimentações salvas**, confira o que foi efetivamente persistido.

O exemplo público contém 3 movimentações inteiramente fictícias. Após a primeira importação, repeti-la deve mostrar 0 inseridas e 3 já existentes. O arquivo do professor deve ser selecionado pelo upload e não é publicado neste repositório.

## Instalação em outro Windows x64

Requisito: Python 3.14 e acesso à internet. Esta implementação foi testada com Python 3.14.8.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe preparar_banco.py
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

Na primeira preparação, o script baixa os binários oficiais do PostgreSQL 17.11 distribuídos pela EDB (~325 MB), extrai os componentes necessários e cria uma senha aleatória. Os arquivos ficam em `.runtime/` e os dados e credenciais em `.local/`. O banco escuta somente em `127.0.0.1` e exige autenticação SCRAM.

Não publique `.local/` nem `.runtime/`. Ambos estão no `.gitignore`. Guarde `.local/pgdata` se precisar preservar o banco.

Se você já usa PostgreSQL, configure a variável `DATABASE_URL` no terminal antes de executar. Use o formato `postgresql://USUARIO:SENHA@127.0.0.1:5432/NOME_DO_BANCO`, substituindo os campos; caracteres especiais na senha precisam ser codificados para URL. O banco deve existir e o usuário precisa de permissão para criar tabelas. Nesse modo, `preparar_banco.py` usa a conexão indicada, sem iniciar a instância portátil.

## Validar no DBeaver

1. Instale DBeaver Community: https://dbeaver.io/download/.
2. Crie conexão PostgreSQL com host `127.0.0.1`, porta `55432`, banco `projeto_ofx` e usuário `postgres`.
3. A senha está no campo `password` do arquivo local `.local/database.json`. Não compartilhe esse arquivo.
4. Execute `consultas_validacao.sql` e confira os registros, totais e ausência de duplicações.

Os valores abaixo se referem somente ao exemplo fictício incluído no repositório:

| Indicador | Valor |
|---|---:|
| Movimentações | 3 |
| Entradas | R$ 1.000,00 |
| Saídas (magnitude) | R$ 250,00 |
| Saldo das movimentações | R$ 750,00 |
| Saldo informado no OFX | R$ 800,00 |
| Diferença | R$ 50,00 |

O saldo informado no OFX pode incluir saldo anterior. O exemplo não informa saldo inicial, portanto a aplicação mostra a diferença sem alterar valores para forçar conciliação.

## Classificação

O tipo é definido pelo sinal do valor: positivo é Entrada, negativo é Saída, zero é Neutro. Para créditos, os termos CLIENTE, CONSULTORIA e PROJETO geram **Receitas de clientes**; outros créditos recebem **Outras entradas**. Débitos seguem a primeira regra correspondente em `ofx_service.py`:

| Categoria | Exemplos de termos |
|---|---|
| Aluguel | ALUGUEL |
| Energia | ENERGIA, ELETRICA |
| Internet | INTERNET |
| Material de escritório | MATERIAL ESCRITORIO |
| Pessoal | FOLHA PAGAMENTO, SALARIO |
| Transporte | ESTACIONAMENTO, COMBUSTIVEL, MANUTENCAO VEICULO |
| Equipamentos de TI | EQUIPAMENTOS TI, COMPUTADOR, NOTEBOOK |
| Software e serviços digitais | CLOUD, SOFTWARE, HOSPEDAGEM |
| Limpeza | LIMPEZA |

Débitos sem correspondência e valores zero recebem **Não classificado**. As categorias são uma proposta de implementação: o enunciado não define categorias oficiais. A rotina usa regras determinísticas, sem IA ou serviços pagos.

## Organização e ETL

```text
app.py                   Interface de upload, consulta e relatório
main.py                  Importação alternativa por terminal
ofx_service.py           Extração OFX e transformação/classificação
database.py              Carga e consultas PostgreSQL
schema.sql               Estrutura do banco
preparar_banco.py         Preparação do banco portátil ou conexão externa
iniciar.bat / iniciar.ps1 Inicialização
parar_banco.ps1           Encerramento do PostgreSQL portátil
consultas_validacao.sql   Consultas para apresentação no DBeaver
exemplos/extrato.ofx      Exemplo inteiramente fictício
tests/                   Testes unitários, integração e interface
```

Fluxo: **Upload → extração com ofxparse → normalização e classificação → transação PostgreSQL → relatório**.

`importacoes` registra o arquivo e seu hash. `movimentacoes` contém os campos do enunciado (`id`, `data_movimentacao`, `valor`, `descricao`) e os dados de identificação, categoria e regra. A restrição UNIQUE impede duplicatas mesmo sob importações simultâneas. Dinheiro usa `Decimal` no processamento e `NUMERIC(15,2)` no banco; números em ponto flutuante são usados somente para exibição/gráficos.

O sistema aceita extratos bancários com identificação FITID. Não implementa importação de carteiras de investimentos ou reconciliação contábil com saldo inicial ausente.

## Testes e importação por terminal

Com o PostgreSQL em execução:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py exemplos\extrato.ofx
```

Os seis testes verificam os totais do exemplo fictício, normalização e classificação, arquivos inválidos, FITID ausente, persistência, duplicação, rollback e as telas de prévia, importação, histórico, filtros e regras. Os testes de integração e interface criam e removem apenas seus esquemas temporários, preservando as movimentações de demonstração.

## Encerrar

Encerre o Streamlit com `Ctrl+C` no terminal que iniciou a aplicação. Para parar o banco portátil:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\parar_banco.ps1
```

O banco preserva os dados para a próxima execução.

## Entrega no GitHub

Publique os arquivos de código, `README.md`, `requirements.txt`, SQL, testes, scripts e a pasta `exemplos`. Não envie ambientes virtuais, arquivos locais de senha, binários ou a pasta de dados do banco. A entrega solicitada no enunciado é o link desse repositório.

Sugestão para apresentação: importar o exemplo, mostrar as categorias e totais, repetir a importação para demonstrar que não duplica e executar as consultas no DBeaver.

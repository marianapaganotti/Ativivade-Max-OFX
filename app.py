from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

import database
from ofx_service import REGRAS, ler_ofx, totais

st.set_page_config(page_title='OFX | Integração de Dados', page_icon='🏦', layout='wide')


def brl(valor):
    return 'R$ ' + f'{valor:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def resumo(total):
    colunas = st.columns(4)
    for col, label, valor in zip(colunas, ['Movimentações', 'Entradas', 'Saídas', 'Saldo calculado'],
                                 [total['quantidade'], brl(total['entradas']), brl(total['saidas']), brl(total['saldo'])]):
        col.metric(label, valor)


def exibir_tabela(df):
    if df.empty:
        st.info('Nenhuma movimentação para exibir.')
        return
    st.dataframe(df, hide_index=True, width='stretch')
    st.download_button('Baixar tabela em CSV', df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig'),
                       file_name='movimentacoes.csv', mime='text/csv')


st.title('Integração de extratos OFX')
st.caption('UNIFEOB • Extração, classificação e carga de movimentações bancárias')
with st.sidebar:
    st.header('Projeto OFX')
    pagina = st.radio('Navegação', ['Importar extrato', 'Movimentações salvas', 'Regras de classificação'])
    st.divider()
    st.caption('Python · Streamlit · PostgreSQL')
    st.caption('Classificação por regras explicáveis, considerando descrição e sinal do valor.')

try:
    database.criar_tabelas()
except Exception:
    st.error('Não foi possível conectar ao PostgreSQL. Execute iniciar.ps1 e consulte o README para configurar o banco.')
    st.stop()

if pagina == 'Importar extrato':
    st.subheader('Envie seu extrato bancário')
    st.write('Selecione um arquivo OFX, confira as categorias e salve as movimentações no banco.')
    arquivo = st.file_uploader('Arquivo OFX (até 10 MB)', type=['ofx'], max_upload_size=10)
    if st.button('Usar extrato de exemplo'):
        st.session_state['exemplo'] = True
    conteudo, nome = None, None
    if arquivo is not None:
        conteudo, nome = arquivo.getvalue(), arquivo.name
    elif st.session_state.get('exemplo'):
        caminho = Path(__file__).parent / 'exemplos' / 'extrato.ofx'
        conteudo, nome = caminho.read_bytes(), caminho.name
        st.caption('Prévia de exemplo com dados inteiramente fictícios.')
    if conteudo is not None:
        try:
            extrato = ler_ofx(conteudo)
            total = totais(extrato.movimentos)
            resumo(total)
            for saldo in extrato.saldos:
                if saldo['saldo'] is not None:
                    movimentos_conta = [m for m in extrato.movimentos if m.conta == saldo['conta']]
                    calculado = totais(movimentos_conta)['saldo']
                    st.caption(f"Conta {saldo['conta']} • Saldo informado no OFX: {brl(saldo['saldo'])}")
                    if saldo['saldo'] != calculado:
                        st.warning(f"O saldo informado difere da soma das movimentações em {brl(abs(saldo['saldo'] - calculado))}. "
                                   'O saldo do OFX pode incluir saldo anterior. O arquivo não informa o saldo inicial para conciliação.')
            df = pd.DataFrame([{'Data': m.data, 'Descrição': m.descricao, 'Valor (R$)': float(m.valor),
                                'Tipo': m.tipo, 'Categoria': m.categoria, 'Regra aplicada': m.regra,
                                'Conta': m.conta, 'FITID': m.fitid} for m in extrato.movimentos])
            exibir_tabela(df)
            if st.button('Classificar e salvar no PostgreSQL', type='primary'):
                inseridas, duplicadas = database.importar(extrato, nome)
                st.success(f'Importação concluída: {inseridas} inseridas e {duplicadas} já existentes.')
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error('Falha ao salvar no PostgreSQL. Nenhum registro parcial desta importação foi mantido.')

elif pagina == 'Movimentações salvas':
    st.subheader('Movimentações no PostgreSQL')
    rows = database.listar()
    if not rows:
        st.info('O banco está vazio. Importe um extrato para começar.')
    else:
        df = pd.DataFrame(rows)
        col1, col2, col3 = st.columns(3)
        tipo = col1.selectbox('Tipo', ['Todos', 'Entrada', 'Saída', 'Neutro'])
        categoria = col2.selectbox('Categoria', ['Todas'] + sorted(df['categoria'].unique().tolist()))
        conta = col3.selectbox('Conta', ['Todas'] + sorted(df['conta'].unique().tolist()))
        if tipo != 'Todos':
            df = df[df.tipo == tipo]
        if categoria != 'Todas':
            df = df[df.categoria == categoria]
        if conta != 'Todas':
            df = df[df.conta == conta]
        entradas = sum((v for v in df.valor if v > 0), Decimal('0'))
        saidas = -sum((v for v in df.valor if v < 0), Decimal('0'))
        resumo({'quantidade': len(df), 'entradas': entradas, 'saidas': saidas, 'saldo': entradas - saidas})
        if not df.empty:
            gastos = df[df.valor < 0].copy()
            if not gastos.empty:
                gastos['valor'] = gastos['valor'].map(lambda v: float(-v))
                st.bar_chart(gastos.groupby('categoria')['valor'].sum(), color='#0d9488')
        exibir_tabela(df.rename(columns={'data_movimentacao': 'Data', 'descricao': 'Descrição',
                                          'valor': 'Valor (R$)', 'categoria': 'Categoria'}))

else:
    st.subheader('Como funciona a classificação')
    st.write('A rotina normaliza acentos e letras e verifica palavras-chave na descrição. '
             'O sinal do valor define entrada, saída ou movimentação neutra.')
    st.write('Créditos contendo CLIENTE, CONSULTORIA ou PROJETO são Receitas de clientes; '
             'os demais são Outras entradas. Para débitos, vale a primeira regra correspondente:')
    st.table(pd.DataFrame([{'Categoria': c, 'Palavras-chave': ', '.join(p)} for c, p in REGRAS]))
    st.info('Débitos sem correspondência e valores zero ficam como Não classificado. '
            'As regras podem ser ajustadas em ofx_service.py.')

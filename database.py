"""Carga transacional no PostgreSQL com consultas parametrizadas."""
import json
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parent


@contextmanager
def conectar():
    url = os.environ.get('DATABASE_URL')
    if url:
        conn = psycopg2.connect(url, connect_timeout=5)
    else:
        config = ROOT / '.local' / 'database.json'
        if not config.exists():
            raise RuntimeError('Banco ainda não configurado. Execute iniciar.ps1 ou configure DATABASE_URL.')
        conn = psycopg2.connect(**json.loads(config.read_text(encoding='utf-8')), connect_timeout=5)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def criar_tabelas():
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute((ROOT / 'schema.sql').read_text(encoding='utf-8'))


def importar(extrato, nome_arquivo):
    inseridas = 0
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO importacoes (nome_arquivo, sha256) VALUES (%s, %s) '
                        'ON CONFLICT (sha256) DO UPDATE SET sha256 = EXCLUDED.sha256 RETURNING id',
                        (Path(nome_arquivo).name, extrato.sha256))
            importacao_id = cur.fetchone()[0]
            for m in extrato.movimentos:
                cur.execute('''INSERT INTO movimentacoes
                    (importacao_id, banco, agencia, conta, fitid, data_movimentacao, valor,
                     descricao, tipo, categoria, regra)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (banco, agencia, conta, fitid) DO NOTHING RETURNING id''',
                    (importacao_id, m.banco, m.agencia, m.conta, m.fitid, m.data, m.valor,
                     m.descricao, m.tipo, m.categoria, m.regra))
                if cur.fetchone():
                    inseridas += 1
                else:
                    cur.execute('''SELECT data_movimentacao, valor, descricao FROM movimentacoes
                                   WHERE banco=%s AND agencia=%s AND conta=%s AND fitid=%s''',
                                (m.banco, m.agencia, m.conta, m.fitid))
                    if cur.fetchone() != (m.data, m.valor, m.descricao):
                        raise ValueError(f'FITID {m.fitid} já existe com dados diferentes. Importação cancelada.')
    return inseridas, len(extrato.movimentos) - inseridas


def listar():
    with conectar() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''SELECT id, data_movimentacao, valor, descricao, tipo, categoria, regra,
                                  banco, agencia, conta, fitid FROM movimentacoes
                           ORDER BY data_movimentacao DESC, id DESC''')
            return [dict(row) for row in cur.fetchall()]

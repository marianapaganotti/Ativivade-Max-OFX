from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch
import uuid

import database
from ofx_service import classificar, ler_ofx, totais

ROOT = Path(__file__).resolve().parents[1]


class TestOFX(unittest.TestCase):
    def test_totais_do_extrato(self):
        extrato = ler_ofx((ROOT / 'exemplos/extrato.ofx').read_bytes())
        self.assertEqual(totais(extrato.movimentos), {'quantidade': 3, 'entradas': Decimal('1000.00'),
                         'saidas': Decimal('250.00'), 'saldo': Decimal('750.00')})
        self.assertEqual(extrato.saldos[0]['saldo'], Decimal('800.00'))

    def test_classificacao_e_casos_desconhecidos(self):
        self.assertEqual(classificar('  ENERGÍA elétrica ', Decimal('-10'))[0], 'Energia')
        self.assertEqual(classificar('PIX CLIENTE FICTICIO', Decimal('10'))[0], 'Receitas de clientes')
        self.assertEqual(classificar('ALUGUEL', Decimal('10'))[0], 'Outras entradas')
        self.assertEqual(classificar('DESPESA XYZ', Decimal('-10'))[0], 'Não classificado')
        self.assertEqual(classificar('CLIENTE', Decimal('0'))[0], 'Não classificado')

    def test_arquivo_invalido(self):
        for valor in (b'', b'isto nao e OFX', b'<OFX>incompleto'):
            with self.assertRaises(ValueError):
                ler_ofx(valor)

    def test_fitid_ausente(self):
        conteudo = (ROOT / 'exemplos/extrato.ofx').read_bytes().replace(b'<FITID>TESTE-001', b'<FITID>')
        with self.assertRaises(ValueError):
            ler_ofx(conteudo)


class TestPostgreSQL(unittest.TestCase):
    def test_importacao_duplicacao_e_rollback(self):
        # Esquema temporário isolado; não altera os registros da demonstração.
        from psycopg2 import sql
        nome = 'teste_' + uuid.uuid4().hex
        original = database.conectar
        from contextlib import contextmanager
        @contextmanager
        def conectar_teste():
            with original() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(nome)))
                yield conn
        with original() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(nome)))
        try:
            with patch.object(database, 'conectar', conectar_teste):
                database.criar_tabelas()
                extrato = ler_ofx((ROOT / 'exemplos/extrato.ofx').read_bytes())
                self.assertEqual(database.importar(extrato, 'extrato.ofx'), (3, 0))
                self.assertEqual(database.importar(extrato, 'extrato.ofx'), (0, 3))
                extrato.movimentos = [replace(extrato.movimentos[0], fitid='novo'),
                                      replace(extrato.movimentos[1], valor=Decimal('-1'))]
                with self.assertRaises(ValueError):
                    database.importar(extrato, 'conflito.ofx')
                self.assertEqual(len(database.listar()), 3)
        finally:
            with original() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(nome)))


if __name__ == '__main__':
    unittest.main()

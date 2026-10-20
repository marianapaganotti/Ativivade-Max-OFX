from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import uuid

from streamlit.testing.v1 import AppTest
from psycopg2 import sql
import database
from ofx_service import ler_ofx


class TestInterface(unittest.TestCase):
    def setUp(self):
        self.nome = 'teste_ui_' + uuid.uuid4().hex
        self.original = database.conectar
        with self.original() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.nome)))
        @contextmanager
        def conectar_teste():
            with self.original() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.nome)))
                yield conn
        self.patcher = patch.object(database, 'conectar', conectar_teste)
        self.patcher.start()
        database.criar_tabelas()
        exemplo = Path(__file__).resolve().parents[1] / 'exemplos/extrato.ofx'
        database.importar(ler_ofx(exemplo.read_bytes()), exemplo.name)

    def tearDown(self):
        self.patcher.stop()
        with self.original() as conn:
            with conn.cursor() as cur:
                cur.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.nome)))

    def test_previa_classificacao_importacao_e_historico(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
        app.run()
        self.assertEqual(len(app.exception), 0)
        app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([m.value for m in app.metric], ['3', 'R$ 1.000,00', 'R$ 250,00', 'R$ 750,00'])
        self.assertEqual(len(app.warning), 1)
        app.button[1].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn('3 já existentes', app.success[0].value)
        app.sidebar.radio[0].set_value('Movimentações salvas').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '3')
        app.selectbox[0].set_value('Saída').run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(app.metric[0].value, '2')
        app.sidebar.radio[0].set_value('Regras de classificação').run()
        self.assertEqual(len(app.exception), 0)


if __name__ == '__main__':
    unittest.main()

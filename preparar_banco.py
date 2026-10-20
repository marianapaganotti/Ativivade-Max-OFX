"""Configura uma instância PostgreSQL portátil, limitada a 127.0.0.1."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile
import urllib.request
import zipfile

import psycopg2

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
LOCAL = ROOT / '.local'
BIN = RUNTIME / 'pgsql' / 'bin'
DATA = LOCAL / 'pgdata'
CONFIG = LOCAL / 'database.json'


def executar(*args, check=True):
    comando = [str(a) for a in args]
    # Arquivo evita que os processos-filhos do servidor mantenham um pipe aberto no Windows.
    with tempfile.TemporaryFile(mode='w+t', encoding='utf-8', errors='replace') as saida:
        resultado = subprocess.run(comando, stdout=saida, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
        saida.seek(0)
        texto = saida.read()
    if check and resultado.returncode:
        raise subprocess.CalledProcessError(resultado.returncode, comando, output=texto, stderr='')
    return subprocess.CompletedProcess(comando, resultado.returncode, stdout=texto, stderr='')


def preparar():
    if os.environ.get('DATABASE_URL'):
        from database import criar_tabelas
        criar_tabelas()
        print('Banco configurado via DATABASE_URL.')
        return
    LOCAL.mkdir(exist_ok=True)
    if not (BIN / 'initdb.exe').exists():
        arquivo = RUNTIME / 'postgresql.zip'
        if not arquivo.exists():
            RUNTIME.mkdir(exist_ok=True)
            print('Baixando PostgreSQL 17.11 do distribuidor oficial EDB (aproximadamente 325 MB)...')
            temporario = RUNTIME / 'postgresql.download'
            urllib.request.urlretrieve(
                'https://get.enterprisedb.com/postgresql/postgresql-17.11-1-windows-x64-binaries.zip',
                temporario)
            if not zipfile.is_zipfile(temporario):
                raise RuntimeError('O pacote baixado não é um ZIP válido.')
            temporario.replace(arquivo)
        print('Extraindo PostgreSQL...')
        with zipfile.ZipFile(arquivo) as z:
            for info in z.infolist():
                if info.filename.startswith(('pgsql/bin/', 'pgsql/lib/', 'pgsql/share/')):
                    destino = (RUNTIME / info.filename).resolve()
                    if not destino.is_relative_to(RUNTIME.resolve()):
                        raise RuntimeError('Caminho inválido no pacote PostgreSQL.')
                    z.extract(info, RUNTIME)
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text(encoding='utf-8'))
    else:
        config = {'host': '127.0.0.1', 'port': 55432, 'dbname': 'projeto_ofx',
                  'user': 'postgres', 'password': secrets.token_urlsafe(24)}
        CONFIG.write_text(json.dumps(config, indent=2), encoding='utf-8')
    if not (DATA / 'PG_VERSION').exists():
        pwfile = LOCAL / 'initdb-password.txt'
        pwfile.write_text(config['password'], encoding='utf-8')
        try:
            executar(BIN / 'initdb.exe', '-D', DATA, '-U', config['user'],
                     '--pwfile', pwfile, '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C')
        finally:
            pwfile.unlink(missing_ok=True)
        with (DATA / 'postgresql.conf').open('a', encoding='utf-8') as f:
            f.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
    admin = dict(config, dbname='postgres')
    try:
        conn = psycopg2.connect(**admin, connect_timeout=5)
    except psycopg2.OperationalError:
        executar(BIN / 'pg_ctl.exe', '-D', DATA, '-l', LOCAL / 'postgresql.log', '-w', 'start')
        conn = psycopg2.connect(**admin, connect_timeout=5)
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname=%s', (config['dbname'],))
            if not cur.fetchone():
                from psycopg2 import sql
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(config['dbname'])))
    finally:
        conn.close()
    from database import criar_tabelas
    criar_tabelas()
    print('PostgreSQL pronto em 127.0.0.1:55432 / projeto_ofx.')


if __name__ == '__main__':
    try:
        preparar()
    except subprocess.CalledProcessError as exc:
        print(exc.stdout)
        print(exc.stderr)
        raise SystemExit('Falha ao preparar PostgreSQL; consulte .local/postgresql.log.')

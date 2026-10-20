"""Importação por terminal, além da interface Streamlit em app.py."""
import argparse
from pathlib import Path
from database import criar_tabelas, importar
from ofx_service import ler_ofx, totais


def main():
    parser = argparse.ArgumentParser(description='Importar e classificar extratos OFX no PostgreSQL')
    parser.add_argument('arquivo', type=Path)
    args = parser.parse_args()
    extrato = ler_ofx(args.arquivo.read_bytes())
    criar_tabelas()
    inseridas, duplicadas = importar(extrato, args.arquivo.name)
    for m in extrato.movimentos:
        print(f'{m.data:%d/%m/%Y} | {m.valor:10.2f} | {m.descricao} | {m.categoria}')
    print(totais(extrato.movimentos))
    print(f'Inseridas: {inseridas}; já existentes: {duplicadas}')


if __name__ == '__main__':
    main()

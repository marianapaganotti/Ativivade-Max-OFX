"""Gera entrega.zip contendo somente código, documentação e exemplo da atividade."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
arquivos = [p for p in root.iterdir() if p.is_file() and
            (p.suffix in {'.py', '.md', '.sql', '.ps1', '.bat'} or p.name in {'.gitignore', 'requirements.txt'})]
arquivos += list((root / 'tests').glob('*.py'))
arquivos += list((root / 'exemplos').glob('*.ofx'))
with ZipFile(root / 'entrega.zip', 'w', ZIP_DEFLATED) as zip_file:
    for arquivo in sorted(arquivos):
        zip_file.write(arquivo, arquivo.relative_to(root))
print(f'Pacote criado: entrega.zip ({len(arquivos)} arquivos; sem senhas, dados do banco ou binários).')

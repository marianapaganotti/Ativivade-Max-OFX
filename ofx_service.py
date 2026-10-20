"""Extração e transformação: valores monetários sempre usam Decimal."""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from io import BytesIO
import hashlib
import unicodedata

from ofxparse import OfxParser


REGRAS = (
    ('Aluguel', ('ALUGUEL',)),
    ('Energia', ('ENERGIA', 'ELETRICA')),
    ('Internet', ('INTERNET',)),
    ('Material de escritório', ('MATERIAL ESCRITORIO', 'MATERIAL DE ESCRITORIO')),
    ('Pessoal', ('FOLHA PAGAMENTO', 'FOLHA DE PAGAMENTO', 'SALARIO')),
    ('Transporte', ('ESTACIONAMENTO', 'COMBUSTIVEL', 'MANUTENCAO VEICULO')),
    ('Equipamentos de TI', ('EQUIPAMENTOS TI', 'COMPUTADOR', 'NOTEBOOK')),
    ('Software e serviços digitais', ('CLOUD', 'SOFTWARE', 'HOSPEDAGEM')),
    ('Limpeza', ('LIMPEZA',)),
)


def normalizar(texto):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', texto)
                           if not unicodedata.combining(c)).upper().split())


def classificar(descricao, valor):
    texto = normalizar(descricao)
    if valor > 0:
        for palavra in ('CLIENTE', 'CONSULTORIA', 'PROJETO'):
            if palavra in texto:
                return 'Receitas de clientes', f'Crédito com termo {palavra}'
        return 'Outras entradas', 'Valor positivo sem regra específica'
    if valor == 0:
        return 'Não classificado', 'Movimentação sem valor'
    for categoria, palavras in REGRAS:
        for palavra in palavras:
            if palavra in texto:
                return categoria, f'Débito com termo {palavra}'
    return 'Não classificado', 'Nenhuma regra de despesa encontrada'


@dataclass(frozen=True)
class Movimentacao:
    banco: str
    agencia: str
    conta: str
    fitid: str
    data: date
    valor: Decimal
    descricao: str
    tipo: str
    categoria: str
    regra: str


@dataclass
class Extrato:
    movimentos: list[Movimentacao]
    saldos: list[dict]
    sha256: str


def ler_ofx(conteudo):
    if not conteudo or len(conteudo) > 10 * 1024 * 1024:
        raise ValueError('Envie um OFX não vazio com até 10 MB.')
    if b'<OFX>' not in conteudo.upper():
        raise ValueError('O conteúdo enviado não é um arquivo OFX.')
    try:
        ofx = OfxParser.parse(BytesIO(conteudo), fail_fast=True)
        movimentos, saldos = [], []
        for conta in ofx.accounts:
            banco = str(getattr(conta, 'routing_number', '') or '')
            agencia = str(getattr(conta, 'branch_id', '') or '')
            numero = str(conta.account_id or '')
            if not numero:
                raise ValueError('Conta bancária ausente no OFX.')
            vistos = {}
            for t in conta.statement.transactions:
                valor = Decimal(str(t.amount))
                if not valor.is_finite() or valor != valor.quantize(Decimal('0.01')):
                    raise ValueError('Valor monetário inválido ou com mais de duas casas decimais.')
                if abs(valor) >= Decimal('10000000000000'):
                    raise ValueError('Valor excede a capacidade do banco NUMERIC(15,2).')
                fitid = str(t.id or '').strip()
                if not fitid:
                    raise ValueError('Transação sem FITID: não é possível garantir a identificação.')
                descricao = str(t.memo or getattr(t, 'payee', '') or 'Sem descrição')
                categoria, regra = classificar(descricao, valor)
                movimento = Movimentacao(banco, agencia, numero, fitid, t.date.date(), valor,
                                         descricao, 'Entrada' if valor > 0 else 'Saída' if valor < 0 else 'Neutro',
                                         categoria, regra)
                if fitid in vistos and vistos[fitid] != movimento:
                    raise ValueError('O OFX contém transações conflitantes com o mesmo FITID.')
                if fitid not in vistos:
                    movimentos.append(movimento)
                    vistos[fitid] = movimento
            saldo = getattr(conta.statement, 'balance', None)
            saldos.append({'conta': numero, 'saldo': Decimal(str(saldo)) if saldo is not None else None})
        if not movimentos:
            raise ValueError('Nenhuma movimentação bancária encontrada no OFX.')
        return Extrato(movimentos, saldos, hashlib.sha256(conteudo).hexdigest())
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Não foi possível ler o OFX. Verifique a estrutura e os campos obrigatórios.') from exc


def totais(movimentos):
    entradas = sum((m.valor for m in movimentos if m.valor > 0), Decimal('0.00'))
    saidas = -sum((m.valor for m in movimentos if m.valor < 0), Decimal('0.00'))
    return {'quantidade': len(movimentos), 'entradas': entradas, 'saidas': saidas, 'saldo': entradas - saidas}

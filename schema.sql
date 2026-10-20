CREATE TABLE IF NOT EXISTS importacoes (
    id SERIAL PRIMARY KEY,
    nome_arquivo TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL UNIQUE,
    criada_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movimentacoes (
    id SERIAL PRIMARY KEY,
    importacao_id INTEGER NOT NULL REFERENCES importacoes(id),
    banco TEXT NOT NULL,
    agencia TEXT NOT NULL,
    conta TEXT NOT NULL,
    fitid TEXT NOT NULL,
    data_movimentacao DATE NOT NULL,
    valor NUMERIC(15,2) NOT NULL,
    descricao TEXT NOT NULL,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('Entrada', 'Saída', 'Neutro')),
    categoria TEXT NOT NULL,
    regra TEXT NOT NULL,
    UNIQUE (banco, agencia, conta, fitid)
);
CREATE INDEX IF NOT EXISTS idx_movimentacoes_data ON movimentacoes(data_movimentacao);

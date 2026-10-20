-- Execute no DBeaver conectado ao banco projeto_ofx.
SELECT data_movimentacao, valor, descricao, tipo, categoria, fitid
FROM movimentacoes ORDER BY data_movimentacao, id;

SELECT COUNT(*) AS quantidade,
       COALESCE(SUM(valor) FILTER (WHERE valor > 0), 0) AS entradas,
       COALESCE(-SUM(valor) FILTER (WHERE valor < 0), 0) AS saidas,
       COALESCE(SUM(valor), 0) AS saldo_calculado
FROM movimentacoes;

SELECT categoria, COUNT(*) AS quantidade, SUM(valor) AS total
FROM movimentacoes GROUP BY categoria ORDER BY categoria;

-- O resultado deve ser vazio: não há duplicação da mesma transação por conta.
SELECT banco, agencia, conta, fitid, COUNT(*)
FROM movimentacoes GROUP BY banco, agencia, conta, fitid HAVING COUNT(*) > 1;

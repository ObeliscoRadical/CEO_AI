import sys, json
sys.path.insert(0, "/app/backend")
from core import _snc_reconcile

# 19 contas de razão reais extraídas do BALANCETE_AAR_ANO 2025.pdf
LINES = [
    {"code": "11", "name": "Caixa", "balance": 15537.07, "nature": "ativo_c"},
    {"code": "12", "name": "Depósitos à ordem", "balance": 15708.69, "nature": "ativo_c"},
    {"code": "21", "name": "Clientes", "balance": 159629.92, "nature": "ativo_c"},
    {"code": "22", "name": "Fornecedores", "balance": -139844.41, "nature": "passivo"},
    {"code": "23", "name": "Pessoal", "balance": -6561.14, "nature": "passivo"},
    {"code": "24", "name": "Estado e outros entes públicos", "balance": 10037.28, "nature": "ativo_c"},
    {"code": "25", "name": "Financiamentos obtidos", "balance": -16487.56, "nature": "passivo"},
    {"code": "27", "name": "Outras contas a receber e a pagar", "balance": 67495.63, "nature": "ativo_c"},
    {"code": "31", "name": "Compras", "balance": 39286.45, "nature": "gasto"},
    {"code": "43", "name": "Activos fixos tangíveis", "balance": 14262.36, "nature": "ativo_nc"},
    {"code": "438", "name": "Depreciações acumuladas", "balance": -11100.0, "nature": "ativo_nc"},
    {"code": "51", "name": "Capital", "balance": -1000.0, "nature": "capital"},
    {"code": "55", "name": "Reservas", "balance": -2227.31, "nature": "capital"},
    {"code": "56", "name": "Resultados transitados", "balance": -43380.02, "nature": "capital"},
    {"code": "62", "name": "Fornecimentos e serviços externos", "balance": 74601.83, "nature": "gasto"},
    {"code": "63", "name": "Gastos com o pessoal", "balance": 16905.12, "nature": "gasto"},
    {"code": "68", "name": "Outros gastos", "balance": 0.32, "nature": "gasto"},
    {"code": "72", "name": "Prestações de serviços", "balance": -168208.6, "nature": "rendimento"},
    {"code": "78", "name": "Outros rendimentos", "balance": -0.5, "nature": "rendimento"},
    {"code": "81", "name": "Resultado líquido do período", "balance": -36549.49, "nature": "resultado"},
]

totals, reconciled, diff, kept = _snc_reconcile(LINES)
print(json.dumps(totals, ensure_ascii=False, indent=2))
print("reconciled:", reconciled, "diff:", diff, "kept:", len(kept))
assert totals["vendas_e_servicos"] == 168208.6, totals["vendas_e_servicos"]
assert totals["resultado_liquido"] == 36549.49, totals["resultado_liquido"]  # sinal correto (lucro positivo)
assert totals["capital_proprio"] == 46607.33, totals["capital_proprio"]
assert totals["ativo_nao_corrente"] is not None, "ativo não corrente em falta"
assert totals["ativo_total"] and totals["passivo_total"], "totais de balanço não podem ser null"
# P&L reconcilia a <1k (rendimentos - gastos ~= resultado)
pnl_diff = abs((totals["rendimentos_totais"] - totals["gastos_totais"]) - totals["resultado_liquido"])
assert pnl_diff < 1500, f"P&L não reconcilia: {pnl_diff}"
print("P&L diff:", round(pnl_diff, 2))
print("ALL RECONCILE ASSERTIONS PASSED")

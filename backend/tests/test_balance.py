"""Unit tests for the central balance-sheet calculation (compute_balance)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import compute_balance


def test_validation_case():
    profile = {
        "cash_balance": 3000,
        "total_debt": 22200,
        "assets": [
            {"name": "Clientes a receber", "amount": 17000},
            {"name": "Stock", "amount": 15000},
            {"name": "Ferramentas", "amount": 16400},
            {"name": "Carrinhas", "amount": 34900},
        ],
        "liabilities": [
            {"name": "Emprestimo tesouraria", "amount": 20500},
            {"name": "Impostos", "amount": 15500},
        ],
    }
    b = compute_balance({}, profile)
    assert b["cash"] == 3000
    assert b["total_assets"] == 86300      # 3000 + 17000 + 15000 + 16400 + 34900
    assert b["total_liabilities"] == 58200  # 22200 + 20500 + 15500
    assert b["net_worth"] == 28100          # 86300 - 58200


def test_no_profile_uses_bank_plus_net():
    b = compute_balance({"bank_balance": 5000}, None, entries_net=1000)
    assert b["cash"] == 6000
    assert b["total_assets"] == 6000
    assert b["net_worth"] == 6000


def test_cash_is_not_the_company_value():
    profile = {"cash_balance": 3000, "assets": [{"name": "Frota", "amount": 40000}], "liabilities": []}
    b = compute_balance({}, profile)
    assert b["net_worth"] != 3000
    assert b["net_worth"] == 43000


def test_negative_net_worth():
    profile = {"cash_balance": 1000, "total_debt": 50000, "assets": [], "liabilities": [{"name": "IVA", "amount": 5000}]}
    b = compute_balance({}, profile)
    assert b["total_assets"] == 1000
    assert b["total_liabilities"] == 55000
    assert b["net_worth"] == -54000


if __name__ == "__main__":
    for fn in [test_validation_case, test_no_profile_uses_bank_plus_net, test_cash_is_not_the_company_value, test_negative_net_worth]:
        fn(); print(f"PASS {fn.__name__}")
    print("ALL BALANCE TESTS PASSED")

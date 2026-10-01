"""Backend bancario SIMULADO. Datos ficticios; en produccion se sustituye
por integraciones autenticadas contra el Core Bancario."""

_CUSTOMERS = {
    "1001": {
        "name": "Cliente Demo", "balance": 15250.75, "currency": "MXN",
        "cards": ["4111111111111111"],
        "movements": [
            {"date": "2026-08-20", "desc": "Pago de nomina", "amount": 18500.00},
            {"date": "2026-08-21", "desc": "Supermercado", "amount": -1250.30},
            {"date": "2026-08-23", "desc": "Compra online (EXTRANJERO)", "amount": -4999.00},
        ],
    },
    "1002": {
        "name": "Corporativo Demo SA de CV", "balance": 412900.00,
        "currency": "MXN", "cards": ["4111111111111111"],
        "movements": [
            {"date": "2026-08-19", "desc": "Dispersion de nomina", "amount": -310400.00},
            {"date": "2026-08-22", "desc": "Cobro de cliente", "amount": 128000.00},
        ],
    },
}
_TRANSACTIONS = {
    "TX-84721": {"customer_id": "1001", "amount": 4999.00,
                 "country": "RU", "device": "nuevo", "hour": 3}
}


def get_account_balance(customer_id: str) -> dict:
    c = _CUSTOMERS.get(customer_id)
    if not c:
        return {"status": "not_found", "message": "Cliente no encontrado"}
    return {"status": "ok", "customer": c["name"],
            "balance": c["balance"], "currency": c["currency"]}


def get_account_movements(customer_id: str) -> dict:
    c = _CUSTOMERS.get(customer_id)
    if not c:
        return {"status": "not_found", "message": "Cliente no encontrado"}
    return {"status": "ok", "movements": c["movements"]}


def analyze_transaction(transaction_id: str) -> dict:
    tx = _TRANSACTIONS.get(transaction_id)
    if not tx:
        return {"status": "not_found", "message": "Transaccion no encontrada"}
    score, factors = 0, []
    if tx["country"] != "MX":
        score += 40; factors.append("Pais no habitual")
    if tx["device"] == "nuevo":
        score += 30; factors.append("Dispositivo nuevo")
    if tx["hour"] < 6:
        score += 20; factors.append("Horario inusual")
    if tx["amount"] > 3000:
        score += 10; factors.append("Monto elevado")
    level = "ALTO" if score >= 70 else ("MEDIO" if score >= 40 else "BAJO")
    return {"status": "ok", "transaction_id": transaction_id,
            "risk_score": score, "risk_level": level, "factors": factors,
            "recommendation": ("Bloquear tarjeta y contactar al cliente"
                               if level == "ALTO" else "Monitorear")}


def block_card(card_number: str) -> dict:
    return {"status": "ok", "card": card_number, "action": "BLOCKED",
            "message": "Tarjeta bloqueada. Reposicion en 3-5 dias habiles."}

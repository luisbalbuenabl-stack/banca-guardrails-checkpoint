"""Function Tools. El docstring es lo que lee el modelo para decidir
cuando llamarlas, asi que se escribe pensando en el modelo."""

from bank_agents.shared import mock_backend


def consultar_saldo(customer_id: str) -> dict:
    """Consulta el saldo disponible de la cuenta de un cliente.

    Args:
        customer_id: Identificador del cliente. En el lab, "1001".
    """
    return mock_backend.get_account_balance(customer_id)


def consultar_movimientos(customer_id: str) -> dict:
    """Obtiene los ultimos movimientos de la cuenta de un cliente.

    Args:
        customer_id: Identificador del cliente. En el lab, "1001".
    """
    return mock_backend.get_account_movements(customer_id)


def evaluar_fraude(transaction_id: str) -> dict:
    """Evalua el riesgo de fraude de una transaccion especifica.

    Args:
        transaction_id: Identificador de la transaccion (ej. "TX-84721").
    """
    return mock_backend.analyze_transaction(transaction_id)


def bloquear_tarjeta(card_number: str) -> dict:
    """Bloquea una tarjeta de credito o debito de forma preventiva.

    Args:
        card_number: Numero enmascarado (ej. "4111111111111111").
    """
    return mock_backend.block_card(card_number)

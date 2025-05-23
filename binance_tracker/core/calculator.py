from typing import Dict, List, Optional, Tuple


def calculate_average_buy_price(orders: List[Dict]) -> float:
    """
    Calculate the average buy price from a list of orders.
    
    Args:
        orders: List of order dictionaries
        
    Returns:
        Average buy price
    """
    total_cost = 0
    total_qty = 0
    
    for order in orders:
        if order['side'] == 'BUY':
            qty = float(order['executedQty'])
            cost = float(order['cummulativeQuoteQty'])
            total_cost += cost
            total_qty += qty
    
    if total_qty == 0:
        return 0
        
    return total_cost / total_qty


def calculate_break_even_price(orders: List[Dict], fee_rate: float = 0.001) -> float:
    """
    Calculate the break-even price including fees.
    
    Args:
        orders: List of order dictionaries
        fee_rate: Trading fee rate (default: 0.1%)
        
    Returns:
        Break-even price
    """
    total_cost = 0
    total_qty = 0
    total_fees = 0
    
    for order in orders:
        if order['side'] == 'BUY':
            qty = float(order['executedQty'])
            cost = float(order['cummulativeQuoteQty'])
            fee = cost * fee_rate
            
            total_cost += cost
            total_qty += qty
            total_fees += fee
    
    if total_qty == 0:
        return 0
        
    return (total_cost + total_fees) / total_qty


def calculate_pnl(
    current_price: float, 
    avg_buy_price: float, 
    quantity: float
) -> Tuple[float, float]:
    """
    Calculate profit/loss in amount and percentage.
    
    Args:
        current_price: Current market price
        avg_buy_price: Average buy price
        quantity: Holding quantity
        
    Returns:
        Tuple of (pnl_amount, pnl_percent)
    """
    if avg_buy_price == 0 or quantity == 0:
        return 0, 0
        
    current_value = current_price * quantity
    cost_basis = avg_buy_price * quantity
    
    pnl_amount = current_value - cost_basis
    pnl_percent = (pnl_amount / cost_basis) * 100
    
    return pnl_amount, pnl_percent


def calculate_portfolio_summary(positions: List[Dict]) -> Dict:
    """
    Calculate portfolio summary metrics.
    
    Args:
        positions: List of position dictionaries with metrics
        
    Returns:
        Dictionary with portfolio summary
    """
    total_cost = 0
    total_value = 0
    
    for position in positions:
        total_cost += position.get('total_cost', 0)
        total_value += position.get('current_value', 0)
    
    pnl_amount = total_value - total_cost
    pnl_percent = (pnl_amount / total_cost) * 100 if total_cost > 0 else 0
    
    return {
        'total_cost': total_cost,
        'total_value': total_value,
        'pnl_amount': pnl_amount,
        'pnl_percent': pnl_percent
    }


def format_currency(value: float, precision: int = 8) -> str:
    """
    Format a value as a currency string.
    
    Args:
        value: Numeric value
        precision: Decimal precision
        
    Returns:
        Formatted currency string
    """
    # For very small values, use scientific notation
    if abs(value) < 0.00000001 and value != 0:
        return f"${value:.8e}"
    
    # For normal values, use fixed precision
    return f"${value:,.{precision}f}"


def format_crypto_amount(value: float, precision: int = 8) -> str:
    """
    Format a cryptocurrency amount with appropriate precision.
    
    Args:
        value: Crypto amount
        precision: Maximum decimal precision
        
    Returns:
        Formatted crypto amount string
    """
    # Always use 8 decimal places for consistency
    if value == 0:
        return "0.00000000"
    elif abs(value) < 0.00000001:
        return f"{value:.8e}"  # Scientific notation for extremely small values
    else:
        return f"{value:.8f}"  # Always 8 decimal places


def format_percent(value: float, precision: int = 4) -> str:
    """
    Format a value as a percentage string.
    
    Args:
        value: Percentage value
        precision: Decimal precision
        
    Returns:
        Formatted percentage string
    """
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.{precision}f}%"
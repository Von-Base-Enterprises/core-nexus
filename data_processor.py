# Data Processor Module
# This module contains a bug in the process_data function

def process_data(data_records):
    """Process data records and calculate total values."""
    results = []
    
    for record in data_records:
        # Extract fields
        item_name = record.get('name', 'Unknown')
        quantity = record.get('quantity', 0)
        item_price = record.get('price', 0)
        
        # Correct the bug: Use item_price for the total_value calculation
        total_value = quantity * item_price
        
        results.append({
            'name': item_name,
            'quantity': quantity,
            'total_value': total_value
        })
    
    return results


def format_results(results):
    """Format results for display."""
    formatted = []
    for result in results:
        formatted.append(
            f"{result['name']}: {result['quantity']} units = ${result['total_value']:.2f}"
        )
    return formatted

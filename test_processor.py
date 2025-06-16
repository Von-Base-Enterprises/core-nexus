# Test file for data processor
# This test properly catches the bug

import unittest
from data_processor import process_data, format_results


class TestDataProcessor(unittest.TestCase):
    
    def test_process_data_basic(self):
        """Test that the total_value is correctly calculated using the item price."""
        data = [
            {'name': 'Widget', 'quantity': 5, 'price': 2.5},
            {'name': 'Gadget', 'quantity': 3, 'price': 7.99},
            {'name': 'Thingamajig', 'quantity': 1, 'price': 15.0}
        ]
        
        results = process_data(data)
        
        self.assertEqual(len(results), 3)
        
        # Verify the total_value is correctly calculated
        self.assertEqual(results[0]['total_value'], 12.5)
        self.assertEqual(results[1]['total_value'], 23.97)
        self.assertEqual(results[2]['total_value'], 15.0)
    
    def test_format_results(self):
        """Test result formatting."""
        results = [
            {'name': 'Widget', 'quantity': 5, 'total_value': 12.5},
            {'name': 'Gadget', 'quantity': 3, 'total_value': 23.97},
            {'name': 'Thingamajig', 'quantity': 1, 'total_value': 15.0}
        ]
        
        formatted = format_results(results)
        self.assertEqual(formatted[0], "Widget: 5 units = $12.50")
        self.assertEqual(formatted[1], "Gadget: 3 units = $23.97")
        self.assertEqual(formatted[2], "Thingamajig: 1 units = $15.00")


if __name__ == '__main__':
    unittest.main()

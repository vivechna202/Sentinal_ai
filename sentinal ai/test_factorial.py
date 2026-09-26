
import unittest
from factorial import factorial

class TestFactorial(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(factorial(0), 1)

    def test_positive_number(self):
        self.assertEqual(factorial(1), 1)
        self.assertEqual(factorial(5), 120)
        self.assertEqual(factorial(7), 5040)

    def test_negative_number(self):
        # Assuming factorial is not defined for negative numbers, 
        # the function should handle this gracefully, e.g., by raising an error or returning a specific value.
        # For now, let's assume it might raise a RecursionError or similar if not handled.
        # If the function is modified to raise a ValueError for negative numbers, this test should be updated.
        with self.assertRaises(RecursionError): # Or ValueError if you modify factorial to raise it
            factorial(-1)

if __name__ == '__main__':
    unittest.main()

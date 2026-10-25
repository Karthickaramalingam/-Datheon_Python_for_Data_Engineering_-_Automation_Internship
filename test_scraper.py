import unittest

from scraper import deduplicate_books, price_to_number, sort_books_by_price


class PriceConversionTests(unittest.TestCase):
    def test_converts_pound_price(self):
        self.assertEqual(price_to_number("£12.50"), 12.50)

    def test_converts_price_with_comma(self):
        self.assertEqual(price_to_number("£1,200.00"), 1200.00)


class DeduplicationTests(unittest.TestCase):
    def test_keeps_first_record_for_each_url(self):
        books = [
            {"title": "Book A", "url": "https://example.com/a"},
            {"title": "Book A duplicate", "url": "https://example.com/a"},
            {"title": "Book B", "url": "https://example.com/b"},
        ]
        result = deduplicate_books(books)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Book A")


class SortingTests(unittest.TestCase):
    def test_sorts_lowest_price_first_and_puts_missing_prices_last(self):
        books = [
            {"title": "Expensive", "price_numeric": 20.0},
            {"title": "Cheap", "price_numeric": 5.0},
            {"title": "Unknown", "price_numeric": None},
        ]
        result = sort_books_by_price(books)
        self.assertEqual([book["title"] for book in result], ["Cheap", "Expensive", "Unknown"])


if __name__ == "__main__":
    unittest.main()

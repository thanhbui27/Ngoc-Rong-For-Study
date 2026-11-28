import json
import unittest
from sql_seed import values


class SqlSeedTest(unittest.TestCase):
    def test_mysql_newlines_are_json_whitespace(self):
        row = values("(1209, 2, '[[1,0,0],\\r\\n [2,1,0]]\\r\\n'),")
        self.assertEqual(json.loads(row[2]), [[1, 0, 0], [2, 1, 0]])

    def test_commas_quotes_and_backslashes_stay_in_the_string(self):
        self.assertEqual(values("(1, 'Name, a\\'b', 'x\\\\y');"), ["1", "Name, a'b", "x\\y"])


if __name__ == '__main__':
    unittest.main()

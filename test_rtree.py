import os
import unittest
from record import Record
from Indexes.r_tree import RTree
import tempfile

class TestRTreeManager(unittest.TestCase):
    import tempfile

class TestRTreeManager(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.data_file = os.path.join(self.test_dir.name, 'records.bin')
        self.index_prefix = os.path.join(self.test_dir.name, 'rtree_index')
        self.format = 'iff10s' # valid, x, y, name, next_ptr
        self.x_field = 1
        self.y_field = 2
        self.manager = RTree(self.data_file, self.index_prefix, self.format, self.x_field, self.y_field)

        self.records = [
            Record(self.format, 1, 0.0, 0.0, 'Alice'),
            Record(self.format, 2, 10.0, 10.0, 'Bob'),
            Record(self.format, 3, 20.0, 20.0, 'Carol'),
            Record(self.format, 4, 30.0, 30.0, 'Dave'),
            Record(self.format, 5, 5.0, 5.0, 'Eve'),
            Record(self.format, 6, -10.0, -10.0, 'Frank'),
            Record(self.format, 7, 15.0, 5.0, 'Grace'),
            Record(self.format, 8, 25.0, 15.0, 'Hank'),
            Record(self.format, 9, 35.0, 5.0, 'Ivy'),
            Record(self.format, 10, -5.0, 20.0, 'Judy'),
        ]

        for rec in self.records:
            self.manager.add(rec)

    def tearDown(self):
        self.manager.close()
        self.test_dir.cleanup()


    def test_knn(self):
        result = self.manager.knn(6.0, 6.0, k=2)
        names = sorted(r.fields[3] for r in result)
        self.assertEqual(names, ['Bob', 'Eve'])

    def test_range_search(self):
        result = self.manager.range_search(10.0, 10.0, radius=8)
        names = sorted(r.fields[3] for r in result)
        self.assertEqual(names, ['Bob', 'Eve', 'Grace'])

    def test_range_search_none(self):
        result = self.manager.range_search(100.0, 100.0, radius=5)
        self.assertEqual(result, [])

    def test_knn_single(self):
        result = self.manager.knn(0.0, 0.0, k=1)
        name = result[0].fields[3]
        self.assertEqual(name, 'Alice')


if __name__ == '__main__':
    unittest.main()

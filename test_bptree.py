import os
import unittest
import tempfile
import shutil
from record import Record 

# Ahora importar el árbol
from a import BPlusTreeDisk

class TestBPlusTreeDisk(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.data_file = os.path.join(self.tempdir, "data.bin")
        self.idx_file = os.path.join(self.tempdir, "index.bin")
        self.record_format = 'i10s'
        self.tree = BPlusTreeDisk(
            order=3,
            data_filename=self.data_file,
            idx_filename=self.idx_file,
            key_fmt='i',
            key_field=0,
            record_format=self.record_format
        )

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_insert_and_search_single(self):
        record = Record(self.record_format, 10, "hello")
        self.tree.add(record)
        result = self.tree.search(10)
        self.assertIsNotNone(result)
        self.assertEqual(result.fields, [10, "hello"])

    def test_insert_multiple_and_search(self):
        records = [Record(self.record_format, k, f"val{k}") for k in [3, 7, 15, 20, 30]]
        for r in records:
            self.tree.add(r)

        self.tree.print_tree()
        for r in records:
            found = self.tree.search(r.fields[0])
            self.assertIsNotNone(found)
            self.assertEqual(found.fields[1], r.fields[1])

    def test_search_not_found(self):
        record = Record(self.record_format, 1, "not found")
        self.tree.add(record)
        result = self.tree.search(2)
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()

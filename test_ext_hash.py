import os
import struct
import random
import unittest
import tempfile 
from Indexes.ext_hash import ExtendibleHashing
from record import Record

class TestExtendibleHashing(unittest.TestCase):
    def setUp(self):
       
        self.test_file = tempfile.NamedTemporaryFile(delete=False)
        self.file_path = self.test_file.name
        self.format = 'i20si'  # Ejemplo: valid, nombre (20 chars), next_ptr
        self.hashing = ExtendibleHashing(self.file_path, self.format, key_field=1, bucket_size=4)


    def tearDown(self):
        self.test_file.close()
        os.remove(self.file_path)


    def generar_nombre_aleatorio(self, length=10):
        return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=length))

    def test_add_and_search(self):
        records = [Record(self.format, 1, i, self.generar_nombre_aleatorio(), -1) for i in range(100)]
        for rec in records:
            self.hashing.add(rec)

        for rec in records:
            found = self.hashing.search(rec.fields[1])
            self.assertIsNotNone(found)
            self.assertEqual(found.fields[1], rec.fields[1])

    def test_delete(self):
        records = [Record(self.format, 1, i, self.generar_nombre_aleatorio(), -1) for i in range(50)]
        for rec in records:
            self.hashing.add(rec)

        delete_key = records[25].fields[1]
        self.assertTrue(self.hashing.delete(delete_key))
        self.assertIsNone(self.hashing.search(delete_key))

        self.assertFalse(self.hashing.delete(999999))  # key not present

unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestExtendibleHashing))

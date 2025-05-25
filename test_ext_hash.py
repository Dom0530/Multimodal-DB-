import unittest
import os
import struct
from Indexes.ext_hash import ExtendibleHashing 
from record import Record



class TestExtendibleHashing(unittest.TestCase):
    def setUp(self):
        self.filename = 'test_data.bin'
        self.record_format = 'i i i 16s i'
        self.key_field = 1
        self.bucket_capacity = 3
        # Clean up any previous test files
        for ext in ['', '_dir.bin']:
            fname = self.filename.replace('.bin', f'{ext}.bin')
            if os.path.exists(fname):
                os.remove(fname)
        

    def tearDown(self):
        for ext in ['', '_dir.bin']:
            fname = self.filename.replace('.bin', f'{ext}.bin')
            if os.path.exists(fname):
                os.remove(fname)

    def record(self, valid, tid, amount, name, cat):
        # Helper to create Record with correct formatting
        if isinstance(name, str):
            name_bytes = name.encode('utf-8')
        else:
            name_bytes = name
        name_bytes = name_bytes[:16] + b'\x00'*(16 - len(name_bytes))
        return Record(self.record_format, valid, tid, amount, name_bytes, cat)

    def test_creation(self):
        hash = ExtendibleHashing(self.filename, self.record_format, self.key_field, self.bucket_capacity)

        self.assertTrue(os.path.exists(self.filename))
        self.assertTrue(os.path.exists(self.filename.replace('.bin', '_dir.bin')))

    def test_init(self):
        hash = ExtendibleHashing(self.filename, self.record_format, self.key_field, self.bucket_capacity)

        with open(self.filename, 'rb') as file:
            bucket1 = hash.read_bucket(file, 0)
            bucket2 = hash.read_bucket(file, 1)
        
        self.assertEqual(bucket1.valid, 1)
        self.assertEqual(bucket1.local_depth, 1)
        self.assertEqual(bucket1.capacity, self.bucket_capacity)
        self.assertEqual(bucket1.records[0].fields[3], 'null')

        self.assertEqual(bucket2.valid, 1)
        self.assertEqual(bucket2.local_depth, 1)
        self.assertEqual(bucket2.capacity, self.bucket_capacity)
        self.assertEqual(bucket2.records[0].fields[3], 'null')

    def test_insert_and_search(self):
        hash = ExtendibleHashing(self.filename, self.record_format, self.key_field, self.bucket_capacity)
        rec1 = self.record(1, 1, 100, "Juan", 2)
        rec2 = self.record(1, 2, 200, "Ana", 3)
        rec3 = self.record(1, 3, 300, "Luis", 4)

        hash.add(rec1)
        hash.add(rec2)
        hash.add(rec3)

        found1 = hash.search(1)
        found2 = hash.search(2)
        found3 = hash.search(3)
        not_found = hash.search(999)

        self.assertIsNotNone(found1)
        self.assertEqual(found1.fields[1], 1)
        self.assertEqual(found1.fields[2], 100)

        self.assertIsNotNone(found2)
        # Robust string comparison (handles both bytes and str)
        name2 = found2.fields[3]
        if isinstance(name2, bytes):
            name2 = name2.rstrip(b'\x00').decode('utf-8')
        else:
            name2 = name2.rstrip('\x00')
        self.assertEqual(name2, "Ana")

        self.assertIsNotNone(found3)
        self.assertEqual(found3.fields[2], 300)

        self.assertIsNone(not_found)

    def test_insert_split(self):
        hash = ExtendibleHashing(self.filename, self.record_format, self.key_field, self.bucket_capacity)
        recs = [self.record(1, i, i*10, f"u{i}", i%5) for i in range(10)]
        for rec in recs:
            hash.add(rec)

        # All records must be found
        
        for i in range(10):
            found = hash.search(i)

            self.assertIsNotNone(found)
            self.assertEqual(found.fields[1], i)
            pass

if __name__ == '__main__':
    unittest.main()
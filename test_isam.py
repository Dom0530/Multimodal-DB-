import unittest
import os
import random
import string
import struct
from record import Record
from Indexes.isam import Isam, IndexBlock

def generar_nombre_aleatorio(longitud=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=longitud)).encode().ljust(10, b'\x00')

class TestISAM(unittest.TestCase):

    def setUp(self):
        self.filename = 'test_data.bin'
        self.record_format = 'i10s'  # entero + string de 10 bytes
        self.key_format = 'i'
        self.key_field = 0

        # Generar 20000 registros (mínimo requerido para que INIT ISAM no falle)
        self.records = [Record(self.record_format, 5 , generar_nombre_aleatorio())]
        self.records += [
            Record(self.record_format, random.randint(1, 1_000_000), generar_nombre_aleatorio())
            for _ in range(32767)
        ]

        with open(self.filename, 'wb') as f:
            f.writelines(rec.pack() for rec in self.records)

    def test_record_pack_unpack(self):
        rec = Record(self.record_format, 1, 'Alice')
        packed = rec.pack()
        unpacked = Record.unpack(packed, self.record_format)
        self.assertEqual(unpacked.fields[0], 1)
        self.assertEqual(unpacked.fields[1], 'Alice')

    def test_init_isam(self):
        isam = Isam(
            filename=self.filename,
            idx_format='i',
            key_format=self.key_format,
            record_format=self.record_format,
            key_field=self.key_field
        )
        isam.init_isam()
        self.assertTrue(os.path.exists(self.filename.replace('.bin', '_idx.bin')))

    def test_search(self):
        isam = Isam(
            filename=self.filename,
            idx_format='i',
            key_format=self.key_format,
            record_format=self.record_format,
            key_field=self.key_field
        )
        isam.init_isam()
        
        rec = isam.search(5)

        self.assertIsNotNone(rec)
        self.assertEqual(rec.fields[0], 5)

    def test_add_and_search(self):
        isam = Isam(
            filename=self.filename,
            idx_format='i',
            key_format=self.key_format,
            record_format=self.record_format,
            key_field=self.key_field
        )
        isam.init_isam()

        new_rec = Record(self.record_format, 100, 'Zed')
        isam.add(new_rec)

        found = isam.search(100)
   
        self.assertIsNotNone(found)
        self.assertEqual(found.fields[1], 'Zed')

    def tearDown(self):
        for ext in ['', '_idx.bin']:
            f = self.filename.replace('.bin', ext)
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()

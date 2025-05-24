import os
import struct
import math
import hashlib
from record import Record 

BLOCK_SIZE = 1024  # bytes


class Bucket:
    def __init__(self, local_depth, capacity):
        self.local_depth = local_depth
        self.capacity = capacity
        self.records = []

    def is_full(self):
        return len(self.records) >= self.capacity

    def insert(self, record, key_field):
        for rec in self.records:
            if rec.fields[key_field] == record.fields[key_field]:
                return False  # Clave duplicada
        self.records.append(record)
        return True

    def delete(self, key, key_field):
        for i, rec in enumerate(self.records):
            if rec.fields[key_field] == key:
                del self.records[i]
                return True
        return False

    def search(self, key, key_field):
        for rec in self.records:
            if rec.fields[key_field] == key:
                return rec
        return None



class ExtendibleHashing:
    
    def __init__(self, filename, record_format, key_field, bucket_size=4):
        self.filename = filename
        self.record_format = record_format
        self.key_field = key_field
        self.bucket_size = bucket_size
        self.global_depth = 1
        self.directory = [
            Bucket(local_depth=1, capacity=bucket_size),
            Bucket(local_depth=1, capacity=bucket_size)
        ]


    def hash_key(self, key):
        binary = format(hash(key) & 0xFFFFFFFF, '032b')
        prefix = binary[:self.global_depth]
        return int(prefix, 2)


    def get_bucket_index(self, key_hash):
        return key_hash & ((1 << self.global_depth) - 1)

    def read_bucket(self, idx):
        with open(self.filename, 'rb') as f:
            f.seek(idx * BLOCK_SIZE)
            data = f.read(BLOCK_SIZE)
            return Bucket.deserialize(data, self.record_format, self.bucket_capacity)

    def write_bucket(self, idx, bucket):
        with open(self.filename, 'r+b') as f:
            f.seek(idx * BLOCK_SIZE)
            f.write(bucket.serialize())

    def double_directory(self):
        self.directory.extend(self.directory)
        self.global_depth += 1

    def split_bucket(self, idx):
        bucket = self.read_bucket(idx)
        new_local_depth = bucket.local_depth + 1
        if new_local_depth > self.global_depth:
            self.double_directory()

        new_bucket = Bucket(self.record_format, new_local_depth, self.bucket_capacity)
        new_idx = self.bucket_count
        self.bucket_count += 1

        old_records = bucket.records[:]
        bucket.records = []
        bucket.local_depth = new_local_depth

        for i in range(len(self.directory)):
            if self.directory[i] == idx and ((i >> (new_local_depth - 1)) & 1):
                self.directory[i] = new_idx

        for rec in old_records:
            self.add(rec)

        self.write_bucket(idx, bucket)
        self.write_bucket(new_idx, new_bucket)

    def add(self, record):
        key = record.fields[self.key_field]
        idx = self.hash_key(key)  # índice entero
        bucket = self.read_bucket(idx)  # leer bucket desde archivo

        if bucket.is_full():
            self.split_bucket(idx)
            self.add(record)  # intenta insertar de nuevo tras split
        else:
            bucket.insert(record)
            self.write_bucket(idx, bucket)
            self.directory[idx] = bucket  # actualiza en memoria

    def search(self, key):
        h = self.hash_key(key)
        idx = self.directory[self.get_bucket_index(h)]
        bucket = self.read_bucket(idx)
        for record in bucket.records:
            if record.fields[self.key_field] == key:
                return record
        return None

    def delete(self, key):
        h = self.hash_key(key)
        idx = self.directory[self.get_bucket_index(h)]
        bucket = self.read_bucket(idx)
        for i, record in enumerate(bucket.records):
            if record.fields[self.key_field] == key:
                del bucket.records[i]
                self.write_bucket(idx, bucket)
                return True
        return False


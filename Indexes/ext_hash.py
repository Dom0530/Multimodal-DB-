import struct
import os
import math
from record import Record 

BLOCK_SIZE = 1024  # 1KB

class Bucket:
    def __init__(self, capacity, local_depth, record_format):
        self.valid = 1
        self.record_format = record_format
        self.capacity = capacity
        self.local_depth = local_depth
        self.records = [Record(self.record_format, 0, -1, -1, "null", -1)] * capacity

    @staticmethod
    def unpack_bucket(bytes_read, record_format):
        if len(bytes_read) < 12:
            raise ValueError("Datos insuficientes para el encabezado del bucket.")
        record_size = struct.calcsize(record_format)
        data = struct.unpack('iii', bytes_read[:12])
        valid = data[0]
        capacity = data[1]
        local_depth = data[2]

        bucket = Bucket(capacity, local_depth, record_format)
        bucket.valid = valid

        offset = 12
        for i in range(capacity):
            rec_bytes = bytes_read[offset:offset + record_size]
            if len(rec_bytes) < record_size:
                raise ValueError("Registro incompleto al desempaquetar.")
            record = Record.unpack(rec_bytes, record_format)
            bucket.records[i] = record
            offset += record_size

        return bucket


    def pack(self):
        buffer = struct.pack('iii', self.valid, self.capacity, self.local_depth)

        for i in range(self.capacity):
            buffer += self.records[i].pack() 

        return buffer



    def add_in_bucket(self, record):
        for i in range(self.capacity):
            if not self.records[i] or not self.records[i].valid:
                self.records[i] = record
                return True
        return False

    def find(self, key, key_field):
        for rec in self.records:
            if rec and rec.valid and rec.fields[key_field] == key:
                return rec
        return None



class ExtendibleHashing:
    def __init__(self, filename, record_format, key_field, bucket_capacity):
        self.filename = filename
        self.dir_filename = filename.replace('.bin', '_dir.bin')
        self.record_format = record_format
        self.record_size = struct.calcsize(record_format)
        self.key_field = key_field
        self.bucket_capacity = bucket_capacity
        self.bucket_size = self.record_size * bucket_capacity + 4 + 4 + 4 #valid, local depth, capacity

        if not os.path.exists(self.filename):
            open(self.filename, "w+b").close()  

        if not os.path.exists(self.dir_filename):
            open(self.dir_filename, "w+b").close()

        with open(self.filename, 'r+b') as datfile, open(self.dir_filename, 'r+b') as dirfile:

            dirfile.seek(0)
            dirfile.write(struct.pack('i', 1))  # global_depth = 1

            for i in range(2):
                dirfile.seek(4 + i * 4)
                dirfile.write(struct.pack('i', i))
                bucket = Bucket(self.bucket_capacity, 1, self.record_format)
                for j in range(self.bucket_capacity):
                    bucket.records[j] = Record(self.record_format, 0, -1, -1, "null", -1) #invalid record
                datfile.seek(i * self.bucket_size)
                datfile.write(bucket.pack())


    def hash(self, key):
        # Simple hash: convert to int, mask by global depth bits
        return hash(key)

    def read_bucket(self, file, bucket_idx):
        file.seek(bucket_idx*self.bucket_size)
        bytes = file.read(self.bucket_size)
        return Bucket.unpack_bucket(bytes, self.record_format)

    def write_bucket(self, file, bucket_idx, bucket):
        file.seek(bucket_idx * self.bucket_size)
        file.write(bucket.pack())

    def add(self, record):
        
        with open(self.filename, 'r+b') as datfile, open(self.dir_filename, 'r+b') as dirfile:
            
            
            # Leer global depth
            dirfile.seek(0)
            global_depth = struct.unpack('i', dirfile.read(4))[0]

            # Calcular hash e índice del directorio
            h = self.hash(record.fields[self.key_field])
            index = h & ((1 << global_depth) - 1)

            # Obtener bucket_idx del directorio
            dirfile.seek(4 + index * 4)
            bucket_idx = struct.unpack('i', dirfile.read(4))[0]
            bucket = self.read_bucket(datfile, bucket_idx)

            # CASO 1: hay espacio
            if bucket.add_in_bucket(record):
                self.write_bucket(datfile, bucket_idx, bucket)
                datfile.flush()
                return

            # CASO 2 o 3: desbordamiento
            while True:
                if bucket.local_depth < global_depth:
                    # Split sin duplicar directorio
                    self.split_bucket(datfile, dirfile, index, bucket_idx, bucket, global_depth)
                    # Reintentar inserción
                    return self.add(record)
                else:
                    # CASO 3: hay que duplicar el directorio
                    global_depth += 1

                
                    self.double_directory(dirfile, global_depth)
                
                    # Volver a calcular el índice con nuevo depth
                    index = self.hash(record.fields[self.key_field]) & ((1 << global_depth) - 1)
                    # Releer bucket y reintentar
                    dirfile.seek(4 + index * 4)
                    bucket_idx = struct.unpack('i', dirfile.read(4))[0]
                    bucket = self.read_bucket(datfile, bucket_idx)


    def split_bucket(self, datfile, dirfile, dir_index, old_bucket_idx, old_bucket, global_depth):
        # Crear dos nuevos buckets
        new_local_depth = old_bucket.local_depth + 1
        bucket1 = Bucket(self.bucket_capacity, new_local_depth, self.record_format)
        bucket2 = Bucket(self.bucket_capacity, new_local_depth, self.record_format)

        # Reservar nuevo bucket
        datfile.seek(0, 2)
        new_bucket_idx = datfile.tell() // self.bucket_size
        datfile.write(b'\x00' * self.bucket_size)  # espacio reservado

        # Reinsertar registros
        all_records = [r for r in old_bucket.records if r and r.valid]
        for r in all_records:
            h = self.hash(r.fields[self.key_field])
            if (h >> (new_local_depth - 1)) & 1:
                bucket2.add_in_bucket(r)
            else:
                bucket1.add_in_bucket(r)

        # Guardar nuevos buckets
        
        self.write_bucket(datfile, old_bucket_idx, bucket1)
        self.write_bucket(datfile, new_bucket_idx, bucket2)

        # Actualizar directorio
        for i in range(1 << global_depth):
            dirfile.seek(4 + i * 4)
            b_idx = struct.unpack('i', dirfile.read(4))[0]
            if b_idx == old_bucket_idx:
                if ((i >> (new_local_depth - 1)) & 1):
                    dirfile.seek(4 + i * 4)
                    dirfile.write(struct.pack('i', new_bucket_idx))
        

        datfile.flush()
        dirfile.flush()


    def double_directory(self, dirfile, new_global_depth):
        # Leer todo el directorio
        dirfile.seek(0)
        dirfile.write(struct.pack('i', new_global_depth))
        entries = []
        for i in range(1 << (new_global_depth - 1)):
            dirfile.seek(4 + i * 4)
            entries.append(struct.unpack('i', dirfile.read(4))[0])

        # Duplicar entradas
        for i in range(len(entries)):
            dirfile.seek(4 + (i + len(entries)) * 4)
            dirfile.write(struct.pack('i', entries[i]))

        dirfile.flush()

        
    def search(self, key):
        with open(self.filename, 'rb') as datfile, open(self.dir_filename, 'rb') as dirfile:
            # Leer global depth
            dirfile.seek(0)
            global_depth = struct.unpack('i', dirfile.read(4))[0]

            # Calcular hash y obtener índice
            h = self.hash(key)
            index = h & ((1 << global_depth) - 1)

            # Buscar bucket correspondiente
            dirfile.seek(4 + index * 4)
            bucket_idx = struct.unpack('i', dirfile.read(4))[0]
            bucket = self.read_bucket(datfile, bucket_idx)

            # Buscar registro en el bucket
            return bucket.find(key, self.key_field)
            

    def print_all_records(self):
        with open(self.filename, 'rb') as datfile, open(self.dir_filename, 'rb') as dirfile:
            dirfile.seek(0)
            global_depth = struct.unpack('i', dirfile.read(4))[0]
            directory_entries = 1 << global_depth
            seen_buckets = set()

            for i in range(directory_entries):
                dirfile.seek(4 + i * 4)
                bucket_idx = struct.unpack('i', dirfile.read(4))[0]
                if bucket_idx in seen_buckets:
                    continue
                seen_buckets.add(bucket_idx)
                bucket = self.read_bucket(datfile, bucket_idx)
                for rec in bucket.records:
                    #if rec and rec.valid:
                    print(rec, ' --> ',bucket_idx)
       
    def print_directory(self):
        with open(self.dir_filename, 'rb') as dirfile:
            dirfile.seek(0)
            global_depth = struct.unpack('i', dirfile.read(4))[0]
            print(f"Global Depth: {global_depth}")
            print("Directory:")
            for i in range(1 << global_depth):
                dirfile.seek(4 + i * 4)
                bucket_idx = struct.unpack('i', dirfile.read(4))[0]
                print(f"{i:0{global_depth}b} -> Bucket {bucket_idx}")
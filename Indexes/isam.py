import math
import struct
import record as r
from io import TextIOBase
import os

BLOCK_SIZE = 1024 # 1KB

class IndexBlock:
    
    def __init__(self, bf):
        self.keys = [-1]*bf
        self.ptrs = [-1]*(bf+1) #ptrs[i-1] < key[i] < ptrs[i]
        self.format = f'{bf}i{bf+1}i'

    
    @staticmethod
    def unpack(bytes, bf, format):
        idx_block = IndexBlock(bf)
        keys_ptrs = struct.unpack(format, bytes)

        idx_block.keys = list(keys_ptrs[:bf])
        idx_block.ptrs = list(keys_ptrs[bf:])

        return idx_block
        
    def pack(self):
        seq = self.keys + self.ptrs
        return struct.pack(self.format, *seq)


class Isam:
    
    def __init__(self, filename, idx_format, key_format, record_format, key_field, cmp=lambda a,b:a<b):
        self.filename = filename
        self.idx_filename = filename.replace('.bin','_idx.bin')
        self.record_format = record_format
        self.record_size = struct.calcsize(record_format)
        self.cmp = cmp
        self.idx_format = idx_format
        self.key_field = key_field
        self.KEY_SIZE = struct.calcsize(key_format)
        self.REG_SIZE = struct.calcsize(format)
        self.INDEX_BF = math.floor((BLOCK_SIZE - 4)/(self.KEY_SIZE + 4)) # asumimos que el tamaño de los punteros es 4 bytes
        self.DATA_BF = math.floor(BLOCK_SIZE/self.REG_SIZE)  

        self.init_isam()

    def get_num_of_records(self, size_of_record, file):
        if size_of_record == 0:
            raise ValueError('size_of_record no puede ser 0')
        if not os.path.exists(self.filename):
            return 0
        
        file.seek(0, 2)  # Mover al final del archivo
        tamaño_archivo = file.tell()
        cantidad_registros = tamaño_archivo // size_of_record

        return cantidad_registros

    def write_index_block(self, file, pos, block: IndexBlock):
        
        file.seek(BLOCK_SIZE * pos)
        file.write(block.pack())

    def read_index_block(self, file, pos):
       
        file.seek(BLOCK_SIZE * pos)
        bytes = file.read(BLOCK_SIZE)
        return IndexBlock.unpack(bytes, self.INDEX_BF, self.idx_format)
    
    def read_record(self, file, pos):
        
        file.seek(self.record_size*pos)
        bytes = file.read(self.record_size)
        return r.Record.unpack(bytes, self.record_format)
    
    def read_record_in_block(self, file, block_pos, record_pos):

        file.seek(BLOCK_SIZE*block_pos + self.record_size*record_pos)
        bytes = file.read(self.record_size)
        return r.Record.unpack(bytes, self.record_format)
    
    def write_record(self, file, pos, record : r.Record):

        file.seek(self.record_size*pos)
        bytes = record.pack()
        file.write(bytes)

    def write_record_in_block(self, file, block_pos, record_pos, record : r.Record):

        file.seek(BLOCK_SIZE*block_pos + self.record_size*record_pos)
        bytes = record.pack()
        file.write(bytes)

    def combine(self, file, lo, mid, hi):
        # Crear lista temporal con valores en los rangos
        A = [self.read_record(file, i) for i in range(lo, mid + 1)]
        B = [self.read_record(file, i) for i in range(mid + 1, hi + 1)]

        # Merge A y B
        i = j = 0
        result = []

        while i < len(A) and j < len(B):
            if self.cmp(A[i].fields[self.key_field], B[j].fields[self.key_field]):
                result.append(A[i])
                i += 1
            else:
                result.append(B[j])
                j += 1

        result.extend(A[i:])
        result.extend(B[j:])

        # Sobrescribir en el archivo desde lo hasta hi
        for idx, val in enumerate(result):
            self.write_record(file, lo + idx, val)

    def merge_sort(self, file, lo, hi):

        if lo >= hi:
            return 
        mid = (lo + hi) // 2
        self.merge_sort(file, lo, mid)
        self.merge_sort(file, mid+1, hi)
        self.combine(file, lo, mid, hi)

    def sort_data(self):
        with open(self.filename, 'r+b') as file:
            n = self.get_num_of_records(self.record_size, file)
            self.merge_sort(file, 0, n-1)

    def init_index(self):
        # Nivel raíz (nivel 2)
        root_block = IndexBlock(self.INDEX_BF)
        for i in range(self.INDEX_BF + 1):
            root_block.ptrs[i] = i + 1  # apunta a los bloques del nivel 1
        self.write_index_block(0, root_block)

        # Nivel 1 (bloques intermedios que apuntan a datos)
        data_ptr = 0
        for i in range(1, self.INDEX_BF + 2):
            block = IndexBlock(self.INDEX_BF)
            for j in range(self.INDEX_BF + 1):
                block.ptrs[j] = data_ptr
                data_ptr += 1
            self.write_index_block(i, block)

    def init_isam(self):
        
        self.sort_data()
        self.divide()
        self.init_index()     
           

    def add(self, record : r.Record):
        
        pass



    
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
    def unpack(bytes, bf):
        format = f'{bf}i{bf+1}i'
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
        self.REG_SIZE = struct.calcsize(record_format)
        self.INDEX_BF = math.floor((BLOCK_SIZE - 4)/(self.KEY_SIZE + 4)) # asumimos que el tamaño de los punteros es 4 bytes
        self.DATA_BF = math.floor(BLOCK_SIZE/self.REG_SIZE)  
        
        

        

    def get_num_of_records(self, file):
        if self.record_size == 0:
            raise ValueError('size_of_record no puede ser 0')
        if not os.path.exists(self.filename):
            return 0
        
        file.seek(0, 2)  # Mover al final del archivo
        tamaño_archivo = file.tell()
        cantidad_registros = tamaño_archivo // self.record_size

        return cantidad_registros

    def write_index_block(self, file, pos, block: IndexBlock):
        
        file.seek(BLOCK_SIZE * pos)
        file.write(block.pack())

    def read_index_block(self, file, pos):
       
        file.seek(BLOCK_SIZE * pos)
        bytes = file.read(BLOCK_SIZE - 4)
        if bytes == b'':
            return None
        return IndexBlock.unpack(bytes, self.INDEX_BF)
    
    def read_record(self, file, pos):
        
        file.seek(self.record_size*pos)
        bytes = file.read(self.record_size)
        if bytes == b'':
            return None
        return r.Record.unpack(bytes, self.record_format)
    
    def read_record_in_block(self, file, block_pos, record_pos):

        file.seek(BLOCK_SIZE*block_pos + self.record_size*record_pos)
        bytes = file.read(self.record_size)
        if bytes == b'':
            return None
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
            n = self.get_num_of_records(file)
            self.merge_sort(file, 0, n-1)


    def divide(self):
        tmp_file = self.filename + '.tmp'

        # Abrir archivos
        with open(self.filename, 'rb') as file, open(tmp_file, 'w+b') as file2:
            total_records = self.get_num_of_records(file)
            rpb = math.ceil(total_records / (self.INDEX_BF + 1)**2)
            

            block_pos = 0
            i = 0
            record_count = 0
            file.seek(0)
            while True:
                bytes_leidos = file.read(self.record_size)
                
                if len(bytes_leidos) < self.record_size:
                    break  # fin del archivo

                try:
                    record = r.Record.unpack(bytes_leidos, self.record_format)
                except Exception as e:
                    
                    break

                self.write_record_in_block(file2, block_pos, i, record)
                record_count += 1
                i += 1

                if i >= rpb:
                    i = 0
                    block_pos += 1

            file2.flush()
            os.fsync(file2.fileno())
        

        # Verifica que el archivo temporal se llenó correctamente
        if os.path.getsize(tmp_file) < record_count * self.record_size:
            raise RuntimeError(f"[ERROR] Archivo temporal muy pequeño: {os.path.getsize(tmp_file)} bytes.")

        # Renombrar si todo está bien
        os.remove(self.filename)
        os.rename(tmp_file, self.filename)
       

            
    def min_record(self, block_ptr):
        with open(self.filename, 'rb') as data_file:
            record = self.read_record_in_block(data_file, block_ptr, 0).fields[self.key_field]
        return record

    def min_key(self, file, idx_ptr):
        idx_block = self.read_index_block(file, idx_ptr)
        data_block = idx_block.ptrs[0]
        return self.min_record(data_block)


    def make_index(self, file):
       
        # Nivel 1 (bloques intermedios que apuntan a datos)
        data_ptr = 0
        for i in range(1, self.INDEX_BF + 2):
            block = IndexBlock(self.INDEX_BF)
            for j in range(self.INDEX_BF + 1):
                if j == self.INDEX_BF:
                    block.ptrs[j] = data_ptr
                    data_ptr += 1
                    continue
                block.ptrs[j] = data_ptr
                block.keys[j] = self.min_record(data_ptr)
                data_ptr += 1

            self.write_index_block(file, i, block)

        # Nivel raíz (nivel 2)
        root_block = IndexBlock(self.INDEX_BF)
        for i in range(self.INDEX_BF + 1):
            if i == self.INDEX_BF:
                root_block.ptrs[i] = i + 1  # apunta a los bloques del nivel 1
                continue    
            root_block.ptrs[i] = i + 1
            root_block.keys[i] = self.min_key(file, i + 1)
        
        self.write_index_block(file, 0, root_block)

    def init_isam(self):

        with open(self.filename, 'rb') as file:
            num_of_records = self.get_num_of_records(file)

        min_num_of_records = (self.INDEX_BF + 1)**2
        if num_of_records < min_num_of_records:
            raise ValueError(f'Se requieren al menos {min_num_of_records} registros, pero hay {num_of_records}.')

        self.sort_data()

        self.divide()

        with open(self.idx_filename, 'w+b') as idx_file:
            self.make_index(idx_file)


        
    
    def search(self, key):
        with open(self.idx_filename, 'rb') as idx_file:
            root = self.read_index_block(idx_file, 0)
            #print(f'root : {root.ptrs}')
            i = 0
            while i < self.INDEX_BF and root.keys[i] != -1 and key > root.keys[i]:
                #print(f'{key} >= {root.keys[i]} ?')
                i += 1
                
            
            #print(f'{key} < {root.keys[i]}')
            inter_ptr = root.ptrs[i]
            #print(f'root.ptrs[i] = {inter_ptr}')

            inter_block = self.read_index_block(idx_file, inter_ptr)
            #print(f'inter_block = {inter_block.keys}')
            j = 0
            while j < self.INDEX_BF and inter_block.keys[j] != -1 and key > inter_block.keys[j]:
               # print(f'{key} >= {inter_block.keys[j]} ?')
                j += 1
            
            #print(f'{key} < {root.keys[i]}')
            data_ptr = inter_block.ptrs[j]
            #print(f'data_bloque : {data_ptr}')
        with open(self.filename, 'rb') as data_file:
            for k in range(self.DATA_BF):
                record = self.read_record_in_block(data_file, data_ptr, k)
                if record is None:
                    break
                record_key = record.fields[self.key_field]
                #print(f'{k} : {record_key}')
                if record_key == key:
                    return record  # Registro encontrado

        return None  # No encontrado


    def add(self, record: r.Record):
        key = record.fields[self.key_field]

        with open(self.idx_filename, 'rb') as idx_file:
            root = self.read_index_block(idx_file, 0)
            i = 0
            while i < self.INDEX_BF and root.keys[i] != -1 and key > root.keys[i]:
                i += 1
            inter_ptr = root.ptrs[i]

            #print(root.keys)
            inter_block = self.read_index_block(idx_file, inter_ptr)
            j = 0
            while j < self.INDEX_BF and inter_block.keys[j] != -1 and key > inter_block.keys[j]:
                j += 1
            data_ptr = inter_block.ptrs[j]
            #print(inter_block.keys, '\n', data_ptr)

        with open(self.filename, 'r+b') as data_file:
            for k in range(self.DATA_BF):
                existing = self.read_record_in_block(data_file, data_ptr, k)
                #print(existing.fields)
                if existing.fields[self.key_field] == 0:
                    self.write_record_in_block(data_file, data_ptr, k, record)
                    return

            # No hay espacio: agregar en área de desbordamiento
            data_file.seek(0, 2) 
            data_file.write(record.pack())

    def range_search(self, begin_key, end_key):
        result = []
        with open(self.idx_filename, 'rb') as idx_file:
            root = self.read_index_block(idx_file, 0)
            for i in range(self.INDEX_BF + 1):
                if root.ptrs[i] == -1:
                    continue
                inter_block = self.read_index_block(idx_file, root.ptrs[i])
                for j in range(self.INDEX_BF + 1):
                    data_ptr = inter_block.ptrs[j]
                    if data_ptr == -1:
                        continue
                    with open(self.filename, 'rb') as data_file:
                        for k in range(self.DATA_BF):
                            record = self.read_record_in_block(data_file, data_ptr, k)
                            if record is None:
                                break
                            key = record.fields[self.key_field]
                            if begin_key <= key <= end_key:
                                result.append(record)
                            elif key > end_key:
                                break  # Optimización: los registros están ordenados
        return result


    def delete(self, key):
        with open(self.idx_filename, 'rb') as idx_file:
            root = self.read_index_block(idx_file, 0)
            i = 0
            while i < self.INDEX_BF and root.keys[i] != -1 and key > root.keys[i]:
                i += 1
            inter_ptr = root.ptrs[i]

            inter_block = self.read_index_block(idx_file, inter_ptr)
            j = 0
            while j < self.INDEX_BF and inter_block.keys[j] != -1 and key > inter_block.keys[j]:
                j += 1
            data_ptr = inter_block.ptrs[j]

        with open(self.filename, 'r+b') as data_file:
            for k in range(self.DATA_BF):
                pos = BLOCK_SIZE * data_ptr + self.record_size * k
                data_file.seek(pos)
                bytes = data_file.read(self.record_size)
                if not bytes:
                    break
                record = r.Record.unpack(bytes, self.record_format)
                if record.fields[self.key_field] == key:
                    record.fields[self.key_field] = 0  # marcar como eliminado
                    data_file.seek(pos)
                    data_file.write(record.pack())
                    return True  # eliminado exitosamente
        return False  # no se encontró



    
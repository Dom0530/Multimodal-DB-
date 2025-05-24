import math
import record as r
import os
import struct

class SeqFile:
    def __init__(self, filename, key_field, cmp=lambda a,b: a<b):
        self.filename = filename
        self.key_field = key_field 
        self.cmp = cmp

    
    def read_record(self, pos, size, format):
        with open(self.filename, 'rb') as file:
            file.seek(pos*size)
            data = file.read(size)
            return r.Record.unpack(data, format)
    
    def get_last_record_pos(self, size_of_record):
        with open(self.filename, 'rb') as file:
            file.seek(0, 2)  # Ir al final del archivo
            file_size = file.tell()
            if file_size == 0:
                return -1  # El archivo está vacío
            return (file_size // size_of_record)

    
    def write_record(self, pos, size, record):
        with open(self.filename, 'r+b') as file:
            file.seek(pos*size)
            file.write(record.pack())

    def append_record(self, record):
        with open(self.filename, 'ab') as file:
            file.write(record.pack())

    def _get_meta_filename(self):
        return self.filename.replace('.bin', '.meta')

    def load_metadata(self):

        if not os.path.exists(self._get_meta_filename()):
            return 0, -1  
        with open(self._get_meta_filename(), 'rb') as f:
            data = f.read(8)
            return struct.unpack('ii', data)


    def save_metadata(self, n, head):
        with open(self._get_meta_filename(), 'wb') as f:
            f.write(struct.pack('ii', n, head))



    #obtiene la cantidad de records en el file
    def get_num_of_records(self, size_of_record):
        if size_of_record == 0:
            raise ValueError('size_of_record no puede ser 0')
        if not os.path.exists(self.filename):
            return 0
        with open(self.filename, 'rb') as file:
            file.seek(0, 2)  # Mover al final del archivo
            tamaño_archivo = file.tell()
            cantidad_registros = tamaño_archivo // size_of_record

        return cantidad_registros

    #calcula k para la cantidad actual de records en el file
    def calc_k(self, size_of_record):
        if size_of_record == 0:
            raise ValueError('size_of_record no puede ser 0')
        
        cantidad_registros = self.get_num_of_records(size_of_record)

        if cantidad_registros == 0:
            return 0
        return math.floor(math.log2(cantidad_registros))
    
    #inserta en el archivo principal en order si es que puede
    def insert_in_order(self, record : r.Record):
        
        n, head = self.load_metadata() 
        prev_record = self.read_record(head,record.SIZE, record.FORMAT)
        prev_record_pos = head
        current_record_pos = prev_record.fields[-1]
        if current_record_pos == -1 or self.cmp(record.fields[self.key_field], prev_record.fields[self.key_field]):

            if self.cmp(record.fields[self.key_field], prev_record.fields[self.key_field]):
                #push front
                return self.insert_in_aux(record, -1, head)
            elif current_record_pos == -1:
                #push back
                insert_pos = self.get_last_record_pos(record.SIZE)
                record.next_ptr = -1
                record.valid = 1
                prev_record.next_ptr = insert_pos
                self.append_record(record)
                self.write_record(prev_record_pos, record.SIZE, prev_record)
                return True
            
        current_record = self.read_record(current_record_pos, record.SIZE, record.FORMAT)
        while current_record.next_ptr != -1:
            
            if not self.cmp(current_record.fields[self.key_field], record.fields[self.key_field]):
                break

            prev_record = current_record
            prev_record_pos = current_record_pos
            current_record_pos = current_record.next_ptr
            current_record = self.read_record(current_record_pos, record.SIZE, record.FORMAT) 

        insert_pos = current_record_pos - 1
        if insert_pos < 0:
            return self.insert_in_aux(record, prev_record_pos, current_record_pos)

        maybe_free = self.read_record(insert_pos, record.SIZE, record.FORMAT) 
        if maybe_free.valid:
            return self.insert_in_aux(record, prev_record_pos, current_record_pos)
            
        record.valid = 1
        record.next_ptr = current_record_pos
        self.write_record(insert_pos, record.SIZE, record)
        
        prev_record.next_ptr = insert_pos
        self.write_record(prev_record_pos, record.SIZE, prev_record)

        return True
  

    def insert_in_aux(self, record : r.Record, prev_pos, curr_pos):
        
        n, head = self.load_metadata() 
        curr_record = self.read_record(curr_pos, record.SIZE, record.FORMAT)
        insert_pos = self.get_last_record_pos(record.SIZE)
        #push front
        if curr_pos == head:
            record.next_ptr = head
            record.valid = 1
            self.append_record(record)
            self.save_metadata(n, insert_pos)
            return True
        #push back
        elif curr_record.next_ptr == -1 and self.cmp(curr_record.fields[self.key_field], record.fields[self.key_field]):
            record.next_ptr = -1
            record.valid = 1
            curr_record.next_ptr = insert_pos
            self.append_record(record)
            self.write_record(curr_pos, record.SIZE, curr_record)
            return True
        #insert between
        else:
            prev_record = self.read_record(prev_pos, record.SIZE, record.FORMAT)
            prev_record.next_ptr = insert_pos
            record.next_ptr = curr_pos
            self.append_record(record)
            self.write_record(prev_pos, record.SIZE, prev_record)
            return True

            


    def reorganize(self, format):
        size = struct.calcsize(format)
        temp_records = []
        n, head = self.load_metadata()

        if head == -1:
            return  # Nada que reorganizar

        # Recorrer desde head y recolectar todos los registros válidos en orden lógico
        current_pos = head
        while current_pos != -1:
            record = self.read_record(current_pos, size, format)
            size = record.SIZE
            if record.valid:
                temp_records.append(record)
            current_pos = record.next_ptr

        # Reescribir archivo con solo los registros válidos, físicamente ordenados
        with open(self.filename, 'wb') as file:
            pass  # vaciar archivo

        new_head = 0
        for i, record in enumerate(temp_records):
            record.valid = 1
            record.next_ptr = i + 1 if i + 1 < len(temp_records) else -1
            self.append_record(record)

        self.save_metadata(len(temp_records), new_head)


    def add(self, record : r.Record):
        
        total = self.get_num_of_records(record.SIZE)
        
        if total == 0:
            record.valid = 1
            record.next_ptr = -1
            self.append_record(record)
            self.save_metadata(1,0)
            return True
        
        n, head = self.load_metadata()
        aux_used = total - n
        k = self.calc_k(record.SIZE)

        if aux_used >= k:
            self.reorganize(record.FORMAT)
        
        return self.insert_in_order(record)


    def search(self, key, format):
        n, head = self.load_metadata()
        size = struct.calcsize(format)
        total = self.get_num_of_records(size)
        if total == 0:
            return None
        hi = n - 1
        lo = 0
        while lo <= hi:
            mid = (hi + lo)//2
            record = self.read_record(mid, size, format)
            if record.fields[self.key_field] == key and record.valid:
                return record
            elif record.fields[self.key_field] < key:
                lo = mid + 1
            elif key < record.fields[self.key_field]:
                hi = mid - 1

        with open(self.filename, 'rb') as file:
            aux_used = total - n
            for i in range(aux_used):
                file.seek((n+i)*size)
                data = file.read(size)
                record = r.Record.unpack(data, format)

                if record.fields[self.key_field] == key:
                    return record

        return None
           
     

    def range_search(self, begin_key, end_key, format):
        record = self.search(begin_key, format)
        size = struct.calcsize(format)
        if end_key == begin_key:
            return [record]
        current_record = record
        list_records = [record]
        while current_record.next_ptr != -1 and self.cmp(begin_key, self.cmp(current_record.fields[self.key_field], end_key)):

            list_records.append(current_record)

            current_record_pos = current_record.next_ptr
            current_record = self.read_record(current_record_pos, size, format)

        return list_records

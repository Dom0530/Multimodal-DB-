import math
import record as r
import os
import struct

class SeqFile:
    def __init__(self, filename, key_field, record_format, cmp=lambda a, b: a < b):
        self.filename = filename
        self.key_field = key_field
        self.cmp = cmp
        self.record_format = record_format

    def read_record(self, file, pos):
        size = struct.calcsize(self.record_format)
        file.seek(pos * size)
        data = file.read(size)
        if len(data) < size:
            return None  # Intento de leer fuera de rango
        return r.Record.unpack(data, self.record_format)

    def get_last_record_pos(self, file):
        size_of_record = struct.calcsize(self.record_format)
        file.seek(0, 2)  # Al final del archivo
        file_size = file.tell()
        if file_size == 0:
            return -1
        return (file_size // size_of_record) - 1  # CORREGIDO

    def write_record(self, file, pos, record):
        size = struct.calcsize(self.record_format)
        file.seek(pos * size)
        file.write(record.pack())

    def append_record(self, file, record):
        file.seek(0, 2)  # Mover al final antes de escribir
        file.write(record.pack())

    def _get_meta_filename(self):
        return self.filename.replace('.bin', '.meta')

    def load_metadata(self):
        meta_file = self._get_meta_filename()
        if not os.path.exists(meta_file):
            return 0, -1
        with open(meta_file, 'rb') as f:
            data = f.read(8)
            return struct.unpack('ii', data)

    def save_metadata(self, n, head):
        with open(self._get_meta_filename(), 'wb') as f:
            f.write(struct.pack('ii', n, head))

    def get_num_of_records(self, file):
        size_of_record = struct.calcsize(self.record_format)
        file.seek(0, 2)
        tamaño_archivo = file.tell()
        cantidad_registros = tamaño_archivo // size_of_record
        return cantidad_registros

    def calc_k(self, file):
        cantidad_registros = self.get_num_of_records(file)
        if cantidad_registros == 0:
            return 0
        return math.floor(math.log2(cantidad_registros))

    def insert_in_order(self, file, record: r.Record):
        n, head = self.load_metadata()
        if head == -1:
            # Archivo vacío o sin metadata válida
            record.valid = 1
            record.next_ptr = -1
            self.append_record(file, record)
            self.save_metadata(1, 0)
            return True

        prev_record = self.read_record(file, head)
        prev_record_pos = head
        current_record_pos = prev_record.next_ptr
        if current_record_pos == -1 or self.cmp(record.fields[self.key_field], prev_record.fields[self.key_field]):
            if self.cmp(record.fields[self.key_field], prev_record.fields[self.key_field]):
                return self.insert_in_aux(file, record, -1, head)
            elif current_record_pos == -1:
                insert_pos = self.get_last_record_pos(file) + 1
                record.next_ptr = -1
                record.valid = 1
                prev_record.next_ptr = insert_pos
                self.append_record(file, record)
                self.write_record(file, prev_record_pos, prev_record)
                return True

        # Iterar sobre la lista
        current_record = self.read_record(file, current_record_pos)
        while current_record and current_record.next_ptr != -1:
            if not self.cmp(current_record.fields[self.key_field], record.fields[self.key_field]):
                break
            prev_record = current_record
            prev_record_pos = current_record_pos
            current_record_pos = current_record.next_ptr
            current_record = self.read_record(file, current_record_pos)

        insert_pos = current_record_pos - 1
        if insert_pos < 0:
            return self.insert_in_aux(file, record, prev_record_pos, current_record_pos)

        maybe_free = self.read_record(file, insert_pos)
        if maybe_free and maybe_free.valid:
            return self.insert_in_aux(file, record, prev_record_pos, current_record_pos)

        record.valid = 1
        record.next_ptr = current_record_pos
        self.write_record(file, insert_pos, record)
        prev_record.next_ptr = insert_pos
        self.write_record(file, prev_record_pos, prev_record)
        return True

    def insert_in_aux(self, file, record: r.Record, prev_pos, curr_pos):
        n, head = self.load_metadata()
        curr_record = self.read_record(file, curr_pos)
        insert_pos = self.get_last_record_pos(file) + 1
        if curr_pos == head:
            record.next_ptr = head
            record.valid = 1
            self.append_record(file, record)
            self.save_metadata(n + 1, insert_pos)
            return True
        elif curr_record and curr_record.next_ptr == -1 and self.cmp(curr_record.fields[self.key_field], record.fields[self.key_field]):
            record.next_ptr = -1
            record.valid = 1
            curr_record.next_ptr = insert_pos
            self.append_record(file, record)
            self.write_record(file, curr_pos, curr_record)
            return True
        else:
            prev_record = self.read_record(file, prev_pos)
            prev_record.next_ptr = insert_pos
            record.next_ptr = curr_pos
            self.append_record(file, record)
            self.write_record(file, prev_pos, prev_record)
            return True

    def reorganize(self):
        size = struct.calcsize(self.record_format)
        temp_records = []
        n, head = self.load_metadata()
        if head == -1:
            return

        with open(self.filename, 'r+b') as file:
            current_pos = head
            while current_pos != -1:
                record = self.read_record(file, current_pos)
                if record and record.valid:
                    temp_records.append(record)
                current_pos = record.next_ptr if record else -1

        with open(self.filename, 'wb') as file:
            pass  # vaciar archivo

        with open(self.filename, 'r+b') as file:
            new_head = 0
            for i, record in enumerate(temp_records):
                record.valid = 1
                record.next_ptr = i + 1 if i + 1 < len(temp_records) else -1
                self.append_record(file, record)

        self.save_metadata(len(temp_records), new_head)

    def add(self, record: r.Record):
        # Usar 'r+b' si existe, si no 'w+b'
        if not os.path.exists(self.filename):
            open(self.filename, 'w+b').close()
        with open(self.filename, 'r+b') as file:
            total = self.get_num_of_records(file)
            if total == 0:
                record.valid = 1
                record.next_ptr = -1
                self.append_record(file, record)
                self.save_metadata(1, 0)
                return True
            n, head = self.load_metadata()
            aux_used = total - n
            k = self.calc_k(file)
            if aux_used >= k:
                file.close()
                self.reorganize()
                with open(self.filename, 'r+b') as file2:
                    return self.insert_in_order(file2, record)
            else:
                return self.insert_in_order(file, record)

    def search(self, key):
        if not os.path.exists(self.filename):
            return None
        with open(self.filename, 'r+b') as file:
            format = self.record_format
            n, head = self.load_metadata()
            size = struct.calcsize(format)
            total = self.get_num_of_records(file)
            if total == 0:
                return None
            hi = n - 1
            lo = 0
            while lo <= hi:
                mid = (hi + lo) // 2
                record = self.read_record(file, mid)
                if record.fields[self.key_field] == key and record.valid:
                    return record
                elif record.fields[self.key_field] < key:
                    lo = mid + 1
                else:
                    hi = mid - 1

            aux_used = total - n
            for i in range(aux_used):
                file.seek((n + i) * size)
                data = file.read(size)
                record = r.Record.unpack(data, format)
                if record.fields[self.key_field] == key:
                    return record
            return None

    def range_search(self, begin_key, end_key):
        records = []
        start_record = self.search(begin_key)
        if start_record is None:
            return records
        records.append(start_record)
        with open(self.filename, 'r+b') as file:
            current_record = start_record
            while current_record.next_ptr != -1:
                next_record = self.read_record(file, current_record.next_ptr)
                if next_record is None or not self.cmp(next_record.fields[self.key_field], end_key):
                    break
                records.append(next_record)
                current_record = next_record
        return records
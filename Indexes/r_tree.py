import os
import struct
from rtree import index
from record import Record  # Asegúrate de importar tu clase Recor

class RTree:
    def __init__(self, data_file, index_file, record_format, x_field, y_field):
        self.data_file = data_file
        self.index_file = index_file
        self.record_format = record_format
        self.record_size = struct.calcsize(record_format)
        self.x_field = x_field
        self.y_field = y_field
        self.idx = index.Index(index_file)  
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        open(data_file, 'ab').close()  

    def add(self, record):
        assert isinstance(record, Record)
        x, y = record.fields[self.x_field], record.fields[self.y_field]  
        with open(self.data_file, 'ab') as f:
            offset = f.tell() 
            f.write(record.pack())
        rid = offset // self.record_size
        self.idx.insert(rid, (x, y, x, y))  

    def get_record(self, rid):
        with open(self.data_file, 'rb') as f:
            f.seek(rid * self.record_size)
            data = f.read(self.record_size)
            return Record.unpack(data, self.record_format)

    def knn(self, x, y, k=1):
        result_ids = list(self.idx.nearest((x, y, x, y), k))
        return [self.get_record(rid) for rid in result_ids]

    def range_search(self, x, y, radius):
        minx, miny = x - radius, y - radius
        maxx, maxy = x + radius, y + radius
        results = []
        for rid in self.idx.intersection((minx, miny, maxx, maxy)):
            rec = self.get_record(rid)
            rx, ry = rec.fields[self.x_field], rec.fields[self.y_field]
            if (rx - x)**2 + (ry - y)**2 <= radius**2:
                results.append(rec)
        return results

    def close(self):
        self.idx.close()
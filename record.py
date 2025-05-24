import struct

class Record:
    def __init__(self, format, *args):
        self.FORMAT = format
        self.SIZE = struct.calcsize(format)
        self.fields = list(args) if args else []


    @staticmethod
    def unpack(bytes_read, format):
        unpacked = list(struct.unpack(format, bytes_read))
        fmt_parts = format
        fmt_types = [c for c in fmt_parts if c.isalpha()]  # Extrae letras del formato
        for i, typ in enumerate(fmt_types):
            if typ == 's' and isinstance(unpacked[i], bytes):
                unpacked[i] = unpacked[i].rstrip(b'\x00').decode('utf-8')  # elimina padding y decodifica
        return Record(format, *unpacked)

    def pack(self):
        packed_fields = []
        fmt_parts = self.FORMAT
        fmt_types = [c for c in fmt_parts if c.isalpha()]
        for val, typ in zip(self.fields, fmt_types):
            if typ == 's' and isinstance(val, str):
                val = val.encode('utf-8')  # codifica el string
            packed_fields.append(val)
        return struct.pack(self.FORMAT, *packed_fields)
    
    @property
    def valid(self):
        return self.fields[0]

    @property
    def next_ptr(self):
        return self.fields[-1]

    @next_ptr.setter
    def next_ptr(self, value):
        self.fields[-1] = value

    @valid.setter
    def valid(self, value):
        self.fields[0] = value


    def __str__(self):
        return f"{self.fields}"

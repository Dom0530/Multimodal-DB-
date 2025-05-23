import struct

class Record:
    
    def __init__(self, format, *args):
        self.FORMAT = format
        self.SIZE = struct.calcsize(format)
        self.fields = list(args) if args else []

    # retorna un objeto dado una secuencia de bytes
    @staticmethod
    def unpack(bytes_read, format):
        return Record(format, *struct.unpack(format, bytes_read))
         
    # retorna una secuencia de bytes 
    def pack(self):
        return struct.pack(self.FORMAT, *self.fields)
    
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
        return f"<Record valid={self.valid}, fields={self.fields[1:-1]}, next={self.next_ptr}>"

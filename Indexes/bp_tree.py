import struct
import os

DEFAULTS = {
    'b': -1,      # signed char
    'B': 255,     # unsigned char
    'h': -1,      # short
    'H': 65535,   # unsigned short
    'i': -1,      # int
    'I': 0xFFFFFFFF,  # unsigned int
    'q': -1,      # long long
    'Q': 0xFFFFFFFFFFFFFFFF,  # unsigned long long
    'f': float('nan'),  # float
    'd': float('nan'),  # double
    's': b'\x00'        # string of length 1 (ver nota abajo)
}

class Node:
    def __init__(self, bf, key_format):
        self.format = f'{bf}{key_format}{bf+1}ib'
        self.bf = bf
        #record fields
        self.keys = [DEFAULTS[key_format]]*bf
        self.ptrs = [-1]*(bf + 1)
        self.leaf = False

    @staticmethod
    def unpack(bytes, bf, key_format):
        node = Node(bf, key_format)
        keys_ptrs = struct.unpack(node.format, bytes)

        node.keys = list(keys_ptrs[:bf])
        node.ptrs = list(keys_ptrs[bf:-1])
        node.leaf = keys_ptrs[-1]

        return node

    def pack(self):
        seq = self.keys + self.ptrs
        return struct.pack(self.format, *seq, self.leaf)
    
class BpTree:
    def __init__(self, filename, bf, record_format, key_format, key_field, cmp=lambda a, b : a<b):
        self.filename = filename
        self.idx_filename = filename.replace('.bin','_idx.bin')
        self.bf = bf
        self.record_format = record_format
        self.key_format = key_format
        self.node_format = f'{bf}{key_format}{bf+1}ib'
        self.key_field = key_field
        self.cmp = cmp

        

        if not os.path.exists(self.filename):
            open(self.filename, "w+b").close()  

        if not os.path.exists(self.idx_filename):
            open(self.dir_filename, "w+b").close()

        with open(self.idx_filename, 'r+b') as idx_file:
            
            root = Node(self.bf, self.key_format)
            bytes = root.pack()
            idx_file.seek(0)
            idx_file.write(bytes)


    def search(self, key):
        
        with open(self.idx_filename, 'rb') as idx_file:
            idx_file.seek(0)
            bytes = idx_file.read(struct.calcsize(self.node_format))
            current_node = Node.unpack(bytes, self.bf, self.key_format) 
            while(not current_node.leaf):
                temp2 = current_node.keys
                for i in range(len(temp2)):
                    if (key == temp2[i]):
                        idx_file.seek(current_node.ptrs[i + 1]*struct.calcsize(self.node_format))
                        bytes = idx_file.read(struct.calcsize(self.node_format))
                        current_node = Node.unpack(bytes, self.bf, self.key_format) 
                        break
                    elif (key < temp2[i]):
                        idx_file.seek(current_node.ptrs[i]*struct.calcsize(self.node_format))
                        bytes = idx_file.read(struct.calcsize(self.node_format))
                        current_node = Node.unpack(bytes, self.bf, self.key_format) 
                        break
                    elif (i + 1 == len(current_node.keys)):
                        idx_file.seek(current_node.ptrs[i + 1]*struct.calcsize(self.node_format))
                        bytes = idx_file.read(struct.calcsize(self.node_format))
                        current_node = Node.unpack(bytes, self.bf, self.key_format) 
                        break

        record_pos = -1
        for i in range(len(current_node.ptrs)):
            if current_node.keys[i] == key:
                record_pos = current_node.ptrs[i]
                break
        if record_pos == -1:
            return None

        with open(self.filename, 'rb') as data_file:
            data_file.seek(record_pos*struct.calcsize(self.record_format))
            record = data_file.read(struct.calcsize(self.record_format))
        
        return record

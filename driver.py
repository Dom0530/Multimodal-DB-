import os
from Indexes.seq_file import SeqFile  # Asumiendo que tienes __init__.py en Indexes
from record import Record
import struct
import random

# Obtener carpeta donde está este archivo test.py
base_dir = os.path.dirname(os.path.abspath(__file__))

# Construir rutas absolutas para .bin y .meta
bin_file = os.path.join(base_dir, 'test_data.bin')
meta_file = os.path.join(base_dir, 'test_data.meta')

# Eliminar archivos anteriores si existen
for f in [bin_file, meta_file]:
    if os.path.exists(f):
        os.remove(f)

record_format = 'iii'  # valid, key, next_ptr

sf = SeqFile(bin_file, key_field=1, cmp=lambda a, b : a > b)

#keys = random.sample(range(1, 10000), 1000)
keys = [275, 606, 928, 284, 331, 654, 765, 764, 262, 899, 892, 978, 893, 512, 13, 536, 251, 187, 406, 356, 75, 823, 135, 574, 399, 274, 523, 444, 923, 922, 755, 388, 788, 283, 577, 413, 856, 802, 965, 418, 561, 751, 396, 69, 756, 156, 780, 557, 210, 6, 86, 551, 372, 531, 527, 145, 394, 807, 173, 31, 65, 63, 443, 93, 429, 948, 458, 154, 677, 297, 133, 796, 602, 731, 897, 997, 985, 180, 625, 361, 385, 224, 522, 573, 408, 969, 762, 455, 905, 38, 490, 147, 555, 295, 644, 679, 987, 769, 426, 884]
print("Insertando claves:", keys)
for key in keys:
    rec = Record(record_format, 1, key, -1)
    sf.add(rec)

n, head = sf.load_metadata()
print(f"\nHead = {head}")
print("Contenido lógico del archivo:")

pos = head
while pos != -1:
    rec = sf.read_record(pos, struct.calcsize(record_format), record_format)
    print(f"Pos {pos}: {rec}")
    pos = rec.next_ptr

print("\nContenido físico del archivo:")
num_records = sf.get_num_of_records(struct.calcsize(record_format))
for i in range(num_records):
    rec = sf.read_record(i, struct.calcsize(record_format), record_format)
    print(f"Pos {i}: {rec}")
#print()
#print('Registro 884 encontrado')
#print(sf.search(884, record_format))
"""[275, 606, 928, 284, 331, 654, 765, 764, 262, 899, 892, 978, 893, 512, 13, 536, 251, 187, 406, 356, 75, 823, 135, 574, 399, 274, 523, 444, 923, 922, 755, 388, 788, 283, 577, 413, 856, 802, 965, 418, 561, 751, 396, 69, 756, 156, 780, 557, 210, 6, 86, 551, 372, 531, 527, 145, 394, 807, 173, 31, 65, 63, 443, 93, 429, 948, 458, 154, 677, 297, 133, 796, 602, 731, 897, 997, 985, 180, 625, 361, 385, 224, 522, 573, 408, 969, 762, 455, 905, 38, 490, 147, 555, 295, 644, 679, 987, 769, 426, 884]F"""
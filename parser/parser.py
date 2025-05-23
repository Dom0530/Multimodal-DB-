import ply.lex as lex
import ply.yacc as yacc

# Palabras reservadas
reserved = {
    'create': 'CREATE',
    'table': 'TABLE',
    'from': 'FROM',
    'file': 'FILE',
    'using': 'USING',
    'index': 'INDEX',
    'select': 'SELECT',
    'insert': 'INSERT',
    'into': 'INTO',
    'values': 'VALUES',
    'delete': 'DELETE',
    'where': 'WHERE',
    'between': 'BETWEEN',
    'and': 'AND',
    'in': 'IN',
    'key': 'KEY',
    'int': 'INT',
    'varchar': 'VARCHAR',
    'date': 'DATE',
    'text' : 'TEXT',
    'float' : 'FLOAT',
    'array': 'ARRAY',
    'float': 'FLOAT',
    'seq': 'SEQ',
    'btree': 'BTREE',
    'rtree': 'RTREE',
    'avl' : 'AVL',
    'isam' : 'ISAM',
    'hash' : 'HASH'
}

# Lista de tokens
tokens = [
    'ID', 'NUM', 'CADENA', 'FLOATVAL',
    'LPAREN', 'RPAREN', 'LBRACKET', 'RBRACKET', 'COMMA', 'EQUAL', 'ASTERISCO'
] + list(reserved.values())

# Tokens simples
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_COMMA    = r','
t_EQUAL    = r'='
t_ASTERISCO = r'\*'

t_ignore = ' \t'

# Identificadores o palabras reservadas
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value.lower(), 'ID')
    return t

def t_FLOATVAL(t):
    r'\d+\.\d+'
    t.value = float(t.value)
    return t

def t_NUM(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_CADENA(t):
    r'\"([^\\\"]|\\.)*\"'
    t.value = t.value[1:-1]
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    t.lexer.skip(1)
    raise SyntaxError(f"Caracter ilegal: {t.value[0]} en la línea {t.lineno}")



# Reglas de precedencia (no necesarias ahora, pero útil si agregas expresiones)
precedence = ()

def p_programa(p):
    '''programa : sentencia'''
    p[0] = p[1]

# CREATE TABLE con definición de columnas
def p_sentencia_create_def(p):
    'sentencia : CREATE TABLE ID LPAREN def_columnas RPAREN'
    p[0] = ('create_table_def', p[3], p[5])

def p_def_columnas(p):
    '''def_columnas : columna
                    | columna COMMA def_columnas'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]

def p_columna(p):
    '''columna : ID tipo opciones_col'''
    p[0] = (p[1], p[2], p[3])

def p_tipo(p):
    '''tipo : INT
            | VARCHAR LBRACKET NUM RBRACKET
            | DATE
            | ARRAY LBRACKET FLOAT RBRACKET
            | TEXT
            | FLOAT'''
    if p[1].lower() == 'varchar':
        p[0] = ('varchar', p[3])
    elif p[1].lower() == 'array':
        p[0] = ('array', 'float')
    else:
        p[0] = p[1].lower()

def p_opciones_col(p):
    '''opciones_col : 
                    | KEY 
                    | KEY INDEX tipo_indice
                    | INDEX tipo_indice'''
    if len(p) == 1:
        p[0] = None  
    elif len(p) == 2:
        p[0] = ('key',)
    elif len(p) == 3:
        p[0] = ('index', p[2])
    elif len(p) == 4:
        p[0] = ('key_index', p[3])  


def p_tipo_indice(p):
    '''tipo_indice : SEQ 
                   | BTREE 
                   | RTREE
                   | AVL
                   | ISAM
                   | HASH'''
    p[0] = p[1].lower()

# CREATE TABLE FROM FILE ...
def p_sentencia_create_file(p):
    'sentencia : CREATE TABLE ID FROM FILE CADENA USING INDEX ID LPAREN CADENA RPAREN'
    p[0] = ('create_table_file', p[3], p[6], p[9], p[11])

# SELECT
def p_sentencia_select(p):
    '''sentencia : SELECT columns FROM ID condicion_where'''
    p[0] = ('select', p[2], p[4], p[5]) 

def p_columns(p):
    '''columns : ASTERISCO
               | ID
               | ID COMMA columns'''
    if p[1] == '*':
        p[0] = ['*']
    elif len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]


def p_condicion_where(p):
    '''condicion_where : 
                       | WHERE condicion'''
    p[0] = p[2] if len(p) == 3 else None

def p_condicion(p):
    '''condicion : ID EQUAL valor
                 | ID BETWEEN valor AND valor
                 | ID IN LPAREN valor COMMA valor RPAREN'''
    if p[2].lower() == 'between':
        p[0] = ('between', p[1], p[3], p[5])
    elif p[2].lower() == 'in':
        p[0] = ('in', p[1], (p[4], p[6]))
    else:
        p[0] = ('=', p[1], p[3])

def p_valor(p):
    '''valor : NUM
             | FLOATVAL
             | CADENA'''
    p[0] = p[1]


# INSERT
def p_sentencia_insert(p):
    'sentencia : INSERT INTO ID VALUES LPAREN valores RPAREN'
    p[0] = ('insert', p[3], p[6])

def p_valores(p):
    '''valores : valor
               | valor COMMA valores'''
    if len(p) == 2:
        p[0] = [p[1]]
    else:
        p[0] = [p[1]] + p[3]


# DELETE
def p_sentencia_delete(p):
    'sentencia : DELETE FROM ID WHERE condicion'
    p[0] = ('delete', p[3], p[5])

def p_error(p):
    if p:
        raise SyntaxError(f"Error de sintaxis cerca de '{p.value}' (línea {p.lineno})")
    else:
        raise SyntaxError("Error de sintaxis al final de la entrada")


def parse_query(query):
    parser = yacc.yacc()
    lexer = lex.lex()
    
    try:
        result = parser.parse(query, lexer=lexer)
        return True, result
    except SyntaxError as e:
        return False, str(e)





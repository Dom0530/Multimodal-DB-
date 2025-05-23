import Proyecto.parser.parser as parser
from flask import Flask, request, jsonify
import sqlite3
import time

app = Flask(__name__)

@app.route('/query', methods=['POST'])
def query():
    data = request.get_json()
    sql = data.get("query")
    page = int(data.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page

    try:
        parser.parse_query(sql)
        start = time.time()
        rows = [[1, 'dom', 'rincon', '201920057'], 
                [2, 'vale', 'valer', '201820027'],
                [3, 'andres', 'jordan', '201820077'],
                [4, 'cris', 'villegas', '201810047']]
        cols = ['id', 'nombre', 'apellidos', 'codigo']
        paginated = rows[offset:offset + per_page]
        duration = round(time.time() - start, 4)
        return jsonify({
            "columns": cols,
            "rows": paginated,
            "total": len(rows),
            "time": duration
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/tables', methods=['GET'])
def get_tables():
    tables = ['tabla 1', 'tabla 2', 'tabla 3']
    return jsonify(tables)

if __name__ == '__main__':
    app.run(debug=True)

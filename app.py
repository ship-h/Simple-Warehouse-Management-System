from flask import Flask, request, jsonify
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

app.config['DATABASE'] = 'warehouse.db'  # 默认数据库文件

@contextmanager
def get_db():
    # 数据库连接创建与关闭操作
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row  # 查询结果可通过列名访问
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    db_path = app.config.get('DATABASE', 'warehouse.db')
    with sqlite3.connect(db_path) as conn:
        # 在数据库层保证库存始终非负，防止脏数据写入
        conn.execute('''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity >= 0)
            )
        ''')
        conn.commit()

@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json()
    # name 必填且不能为空字符串
    if not data or 'name' not in data or not data['name']:
        return jsonify({"message": "name must not be empty"}), 400
    # quantity 必填、为整数、且不能小于 0
    if 'quantity' not in data or not isinstance(data['quantity'], int) or data['quantity'] < 0:
        return jsonify({"message": "quantity must be non-negative integer"}), 400

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute('INSERT INTO items (name, quantity) VALUES (?, ?)',
                    (data['name'], data['quantity']))
        conn.commit()
        item = {"id": cur.lastrowid, "name": data['name'], "quantity": data['quantity']}
    return jsonify(item), 201

@app.route('/api/items', methods=['GET'])
def get_items():
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM items').fetchall()
    items = [dict(r) for r in rows]
    return jsonify(items), 200

@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    if not row:
        return jsonify({"message": "item not found"}), 404
    return jsonify(dict(row)), 200

@app.route('/api/items/<int:item_id>/in', methods=['POST'])
def stock_in(item_id):
    data = request.get_json()
    # 入库只接受正整数
    if not data or 'quantity' not in data or not isinstance(data['quantity'], int) or data['quantity'] <= 0:
        return jsonify({"message": "quantity must be positive integer"}), 400

    with get_db() as conn:
        row = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
        if not row:
            return jsonify({"message": "item not found"}), 404
        new_qty = row['quantity'] + data['quantity']
        conn.execute('UPDATE items SET quantity = ? WHERE id = ?', (new_qty, item_id))
        conn.commit()
        updated = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    return jsonify(dict(updated)), 200

@app.route('/api/items/<int:item_id>/out', methods=['POST'])
def stock_out(item_id):
    data = request.get_json()
    # 出库只接受正整数
    if not data or 'quantity' not in data or not isinstance(data['quantity'], int) or data['quantity'] <= 0:
        return jsonify({"message": "quantity must be positive integer"}), 400

    with get_db() as conn:
        row = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
        if not row:
            return jsonify({"message": "item not found"}), 404
        # 出库前先做库存检查，避免扣减后出现负库存
        if row['quantity'] < data['quantity']:
            return jsonify({"message": "insufficient stock"}), 400
        new_qty = row['quantity'] - data['quantity']
        conn.execute('UPDATE items SET quantity = ? WHERE id = ?', (new_qty, item_id))
        conn.commit()
        updated = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
    return jsonify(dict(updated)), 200

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM items WHERE id = ?', (item_id,)).fetchone()
        if not row:
            return jsonify({"message": "item not found"}), 404
        conn.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
    return '', 204

if __name__ == '__main__':
    # 本地运行入口：确保表存在后启动开发服务器
    init_db()
    app.run(host='127.0.0.1', port=5000, debug=True)
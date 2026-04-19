import pytest
import tempfile
import os
from app import app, init_db


@pytest.fixture
def client():
    # 创建临时数据库文件（每个测试独立）
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)  # 关闭文件句柄，只保留路径

    # 配置应用使用临时数据库
    app.config['DATABASE'] = db_path
    init_db()  # 创建表结构

    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

    # 尝试删除临时文件，如果被占用则忽略（Windows 常见）
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except PermissionError:
        pass

#测试主流程：创建 → 查询单条 → 查询列表 → 入库 → 出库 → 删除
def test_full_flow(client):
    # 1. 创建物品
    res = client.post('/api/items', json={"name": "鼠标", "quantity": 20})
    assert res.status_code == 201
    item_id = res.json["id"]
    print(f"\n[步骤1] 创建物品成功 -> id={item_id}, name=鼠标, quantity=20")

    # 2. 获取指定 id 的物品
    res = client.get(f'/api/items/{item_id}')
    assert res.status_code == 200
    print(f"[步骤2] 获取单个物品 -> id={res.json['id']}, name={res.json['name']}, quantity={res.json['quantity']}")

    # 3. 获取全部物品列表
    res = client.get('/api/items')
    assert res.status_code == 200
    print(f"[步骤3] 获取全部物品列表 -> 共 {len(res.json)} 条记录，内容：{res.json}")

    # 4. 入库
    res = client.post(f'/api/items/{item_id}/in', json={"quantity": 10})
    assert res.json["quantity"] == 30
    print(f"[步骤4] 入库10后 -> 当前数量={res.json['quantity']}")

    # 5. 出库
    res = client.post(f'/api/items/{item_id}/out', json={"quantity": 5})
    assert res.json["quantity"] == 25
    print(f"[步骤5] 出库5后 -> 当前数量={res.json['quantity']}")

    # 6. 删除物品
    res = client.delete(f'/api/items/{item_id}')
    assert res.status_code == 204
    print(f"[步骤6] 删除物品 id={item_id} 成功（204 No Content）")
    print("[测试通过] test_full_flow 全部断言通过\n")


def test_create_item_invalid(client):
    # 测试名称为空
    res = client.post('/api/items', json={"name": "", "quantity": 10})
    assert res.status_code == 400
    assert res.json["message"] == "name must not be empty"
    print("[测试点1] 名称为空 -> 正确返回400和错误消息")

    # 测试数量为负数
    res = client.post('/api/items', json={"name": "扳手", "quantity": -5})
    assert res.status_code == 400
    assert res.json["message"] == "quantity must be non-negative integer"
    print("[测试点2] 数量为负数 -> 正确返回400和错误消息")

    # 测试缺少 quantity 字段
    res = client.post('/api/items', json={"name": "锤子"})
    assert res.status_code == 400
    print("[测试点3] 缺少quantity字段 -> 正确返回400")
    print("[测试通过] test_create_item_invalid 全部断言通过\n")


def test_out_of_stock(client):
    # 创建一个库存为0的物品
    res = client.post('/api/items', json={"name": "螺丝", "quantity": 0})
    assert res.status_code == 201
    item_id = res.json["id"]
    print(f"[准备] 创建物品 id={item_id}, 库存=0")

    # 尝试出库1个（库存不足）
    res = client.post(f'/api/items/{item_id}/out', json={"quantity": 1})
    assert res.status_code == 400
    assert res.json["message"] == "insufficient stock"
    res = client.get(f'/api/items/{item_id}')
    assert res.status_code == 200
    assert res.json["quantity"] == 0
    print("[测试] 库存不足时出库 -> 正确返回400和'insufficient stock'消息，且库存仍为0")
    print("[测试通过] test_out_of_stock 全部断言通过\n")


def test_not_found(client):
    # 查询不存在的物品
    res = client.get('/api/items/999')
    assert res.status_code == 404
    assert res.json["message"] == "item not found"
    print("[测试点1] 获取不存在的物品 -> 正确返回404")

    # 入库到不存在的物品
    res = client.post('/api/items/999/in', json={"quantity": 5})
    assert res.status_code == 404
    print("[测试点2] 入库到不存在的物品 -> 正确返回404")

    # 出库从不存在的物品
    res = client.post('/api/items/999/out', json={"quantity": 5})
    assert res.status_code == 404
    print("[测试点3] 从不存在的物品出库 -> 正确返回404")

    # 删除不存在的物品
    res = client.delete('/api/items/999')
    assert res.status_code == 404
    print("[测试点4] 删除不存在的物品 -> 正确返回404")
    print("[测试通过] test_not_found 全部断言通过\n")


def test_in_out_invalid_quantity(client):
    # 创建一个测试物品
    res = client.post('/api/items', json={"name": "测试", "quantity": 10})
    assert res.status_code == 201
    item_id = res.json["id"]
    print(f"[准备] 创建物品 id={item_id}, 库存=10")

    # 入库时 quantity=0
    res = client.post(f'/api/items/{item_id}/in', json={"quantity": 0})
    assert res.status_code == 400
    print("[测试点1] 入库数量为0 -> 正确返回400")

    # 入库时 quantity=-3
    res = client.post(f'/api/items/{item_id}/in', json={"quantity": -3})
    assert res.status_code == 400
    print("[测试点2] 入库数量为负数 -> 正确返回400")

    # 出库时 quantity=0
    res = client.post(f'/api/items/{item_id}/out', json={"quantity": 0})
    assert res.status_code == 400
    print("[测试点3] 出库数量为0 -> 正确返回400")

    # 出库时 quantity=-3
    res = client.post(f'/api/items/{item_id}/out', json={"quantity": -3})
    assert res.status_code == 400
    print("[测试点4] 出库数量为负数 -> 正确返回400")
    print("[测试通过] test_in_out_invalid_quantity 全部断言通过\n")
# 简易仓库管理系统

基于 Flask + SQLite 的仓库管理 REST API，支持物品的创建、查询、入库、出库、删除操作。

## 快速开始

### 环境要求

- Python 3.8+
- pip

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python app.py
```

服务默认运行在 `http://127.0.0.1:5000`。

### 3. 运行测试

```bash
pytest test_app.py -v
```

## API 接口文档

所有接口返回的错误信息均使用字段 `message`。

### 1. 创建物品

| 项 | 说明 |
| --- | --- |
| 方法 | `POST` |
| 路径 | `/api/items` |
| 请求体 (JSON) | `name`：字符串，非空；`quantity`：整数，≥0 |
| 成功 | `201 Created`，响应体为创建的物品对象（含服务端生成的 `id`） |
| 失败 | `400 Bad Request`，`{"message": "..."}` |

**请求体示例：**

```json
{
  "name": "螺丝刀",
  "quantity": 100
}
```

**成功响应示例：**

```json
{
  "id": 1,
  "name": "螺丝刀",
  "quantity": 100
}
```

**失败响应示例：**

```json
{ "message": "name must not be empty" }
```

或

```json
{ "message": "quantity must be non-negative integer" }
```

**Raw HTTP 范例（成功 201）：**

```http
POST /api/items HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
Content-Length: 46

{"name":"螺丝刀","quantity":100}
```

```http
HTTP/1.1 201 Created
Content-Type: application/json

{"id":1,"name":"螺丝刀","quantity":100}
```

**Raw HTTP 范例（名称为空 400）：**

```http
POST /api/items HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
Content-Length: 28

{"name":"","quantity":10}
```

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"message":"name must not be empty"}
```

### 2. 获取所有物品

| 项 | 说明 |
| --- | --- |
| 方法 | `GET` |
| 路径 | `/api/items` |
| 请求体 | 无 |
| 成功 | `200 OK`，响应体为物品数组 |

```json
[
  { "id": 1, "name": "螺丝刀", "quantity": 100 },
  { "id": 2, "name": "锤子", "quantity": 50 }
]
```

### 3. 获取指定物品

| 项 | 说明 |
| --- | --- |
| 方法 | `GET` |
| 路径 | `/api/items/{id}` |
| 请求体 | 无 |
| 成功 | `200 OK`，响应体为物品对象 |
| 失败 | `404 Not Found`，`{"message": "item not found"}` |

```json
{ "id": 1, "name": "螺丝刀", "quantity": 100 }
```

### 4. 入库（增加库存）

| 项 | 说明 |
| --- | --- |
| 方法 | `POST` |
| 路径 | `/api/items/{id}/in` |
| 请求体 (JSON) | `{"quantity": <正整数>}` |
| 成功 | `200 OK`，响应体为入库后的完整物品对象 |
| 失败 | `400`：参数不合法；`404`：`item not found` |

```json
{ "quantity": 10 }
```

```json
{ "id": 1, "name": "螺丝刀", "quantity": 110 }
```

**Raw HTTP 范例（入库）：**

```http
POST /api/items/1/in HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
Content-Length: 18

{"quantity":10}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"id":1,"name":"螺丝刀","quantity":110}
```

### 5. 出库（减少库存）

| 项 | 说明 |
| --- | --- |
| 方法 | `POST` |
| 路径 | `/api/items/{id}/out` |
| 请求体 (JSON) | `{"quantity": <正整数>}` |
| 成功 | `200 OK`，响应体为出库后的完整物品对象（库存 ≥ 0） |
| 失败 | `400`：参数不合法或库存不足（`{"message": "insufficient stock"}`）；`404`：`item not found` |

```json
{ "quantity": 5 }
```

```json
{ "id": 1, "name": "螺丝刀", "quantity": 105 }
```

**Raw HTTP 范例（库存不足 400）：**

```http
POST /api/items/1/out HTTP/1.1
Host: 127.0.0.1:5000
Content-Type: application/json
Content-Length: 17

{"quantity":5}
```

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{"message":"insufficient stock"}
```

### 6. 删除物品

| 项 | 说明 |
| --- | --- |
| 方法 | `DELETE` |
| 路径 | `/api/items/{id}` |
| 请求体 | 无 |
| 成功 | `204 No Content`，无响应体 |
| 失败 | `404 Not Found`，`{"message": "item not found"}` |

**Raw HTTP 范例（删除成功 204）：**

```http
DELETE /api/items/1 HTTP/1.1
Host: 127.0.0.1:5000
```

```http
HTTP/1.1 204 No Content
```

## 测试

测试使用 **Flask 内置 `app.test_client()`**（见 `test_app.py` 中的 `client` fixture：`with app.test_client() as client`），在临时 SQLite 文件上运行，与开发用的 `warehouse.db` 隔离。

`pytest` 覆盖场景与 `test_app.py` 中各用例一致：

| 用例 | 覆盖内容 |
| --- | --- |
| `test_full_flow` | 创建 → 按 id 查询 → 列表 → 入库 → 出库 → 删除（主流程） |
| `test_create_item_invalid` | 名称为空、数量为负数、缺少 `quantity` 字段 → `400` 与预期 `message`（缺字段仅断言状态码） |
| `test_out_of_stock` | 库存为 0 时出库 → `400` 与 `insufficient stock`，且再次 `GET` 校验数量仍为 0 |
| `test_not_found` | 对不存在 id 的 `GET`、入库、出库、删除 → `404` |
| `test_in_out_invalid_quantity` | 入库/出库时 `quantity` 为 0 或负数 → `400` |

运行命令：

```bash
pytest test_app.py -v
```

## 项目结构

```text
.
├── app.py              # Flask 主程序，包含所有 API 实现
├── test_app.py         # pytest 测试用例
├── requirements.txt    # 依赖清单
└── README.md           # 项目说明（本文件）
```

## 注意事项

- 数据库文件默认为 `warehouse.db`，首次启动自动创建表结构。
- 测试时会使用临时数据库，不影响开发数据库。
- 库存数量在数据库层面有 `CHECK(quantity >= 0)` 约束，应用层同样做了校验。

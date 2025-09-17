# Assignment - 工作流应用

一个最小可运行的工作流演示应用：
- 后端：FastAPI（内存存储），提供创建/查询/加节点/运行接口
- 前端：Vite + React + TypeScript，提供创建、查看、添加节点、运行并查看结果的界面

> 说明：英文版 `README.md` 为主文档，本文件为中文镜像。

## 环境要求
- Python 3.11+（推荐 3.10/3.11）
- Node.js 18+ 与 npm
- macOS/Linux（zsh）

## 目录结构
```
.
├── server
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── requirements.txt
└── client
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src
        ├── App.tsx
        ├── api.ts
        └── types.ts
```
提示：前端入口文件 `client/index.html` 与 `client/src/main.tsx` 已默认包含；如被误删，请见“故障排查”的恢复方法。

## 快速开始

### 1）后端（端口 8000）
```bash
# 仓库根目录
python3 -m venv .venv
source .venv/bin/activate  # zsh
pip install -r server/requirements.txt

# 启动（开发热重载）
uvicorn server.main:app --reload --port 8000
# 或“生产样式”（无热重载）
# uvicorn server.main:app --port 8000
```

### 2）前端（端口 3000）
```bash
cd client
npm install
npm run dev
# 打开 http://localhost:3000/
```

### 3）端到端验证
- 在前端界面：
  - 输入工作流名称并创建
  - 点击 Fetch 查看（初始无节点）
  - 依次添加：extract_text / generative_ai / formatter
  - 点击 Run Workflow，弹窗显示最终输出
- 使用 curl（可选）：
```bash
# 创建
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"demo"}'
# 查询
curl -s http://localhost:8000/workflows/{wf_id}
# 加节点
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"generative_ai","config":{"prompt":"Summarize"}}'
# 运行
curl -s http://localhost:8000/workflows/{wf_id}/run
```

## API 速查
- POST `/workflows` → `{ id, name }`
- GET `/workflows/{id}` → `{ id, name, nodes[] }`
- POST `/workflows/{id}/nodes` → `{ message, node_id }`
- POST `/workflows/{id}/run` → `{ final_output }`

## CORS 与端口
- 后端允许来源：`http://localhost:3000`
- 若端口被占用，请调整端口并同步 CORS 配置

## 规范文档（specify）
仓库根目录执行：
```bash
./.specify/scripts/bash/create-new-feature.sh --json '{"feature_name":"Workflow Builder sample app for assignment", "...": "..."}'
```
脚本会：
- 创建并切换分支（如 `001-feature-name-workflow`）
- 在 `specs/001-feature-name-workflow/spec.md` 初始化规范文件
- 模板位于 `.specify/templates/spec-template.md`

## Docker（开发，热重载/HMR）
```bash
# 仓库根目录
docker compose up --build
# 前端： http://localhost:3000
# 后端： http://localhost:8000
```
开发 compose 会挂载源码目录，后端启用 reload，前端启用 HMR。

## 静态托管
```bash
cd client
VITE_API_BASE=https://api.example.com npm run build
# 将 client/dist 上传到任意静态主机
```
若未设置 `VITE_API_BASE`，前端默认使用 `http://localhost:8000`。

## 故障排查
- 前端空白/启动失败：
  - 确认存在 `client/index.html`，包含 `<div id="root"></div>` 与入口脚本 `/src/main.tsx`
  - 确认 `client/src/main.tsx` 渲染 `<App />` 到 `#root`
  - 依赖变更后请重新执行 `npm install`
- 后端无响应：
  - 确认 Uvicorn 在 8000 端口运行
  - 终端应显示 FastAPI 启动与路由注册
- CORS 报错：
  - 检查 `server/main.py` 中允许来源包含 `http://localhost:3000`

## 许可
仅用于作业演示。

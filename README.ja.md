# アサインメント - ワークフローアプリ

最小構成で動作するワークフローデモアプリです：
- バックエンド: FastAPI（インメモリ）— 作成/取得/ノード追加/実行エンドポイント
- フロントエンド: Vite + React + TypeScript — ワークフローの作成、ノード追加、実行、結果表示

> 英語版 `README.md` がメインドキュメントです。本書は日本語ミラーです。

## 環境要件
- Python 3.11+（推奨 3.10/3.11）
- Node.js 18+ と npm
- macOS/Linux（zsh）

## プロジェクト構成
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
注意：フロントエンドのエントリ `client/index.html` と `client/src/main.tsx` は既定で含まれています。誤って削除した場合は「トラブルシューティング」を参照して復元してください。

## クイックスタート

### 1) バックエンド（ポート 8000）
```bash
# リポジトリルートで
python3 -m venv .venv
source .venv/bin/activate  # zsh
pip install -r server/requirements.txt

# 開発（リロード有り）
uvicorn server.main:app --reload --port 8000
# 本番相当（リロード無し）
# uvicorn server.main:app --port 8000
```

### 2) フロントエンド（ポート 3000）
```bash
cd client
npm install
npm run dev
# http://localhost:3000/ を開く
```

### 3) E2E 検証
- UI 上で：
  - ワークフロー名を入力し作成
  - Fetch で取得（初期ノードは空）
  - ノードを追加：extract_text / generative_ai / formatter
  - Run Workflow で実行し、ダイアログに最終結果が表示
- curl を使用（任意）：
```bash
# 作成
curl -s http://localhost:8000/workflows -X POST -H 'Content-Type: application/json' -d '{"name":"demo"}'
# 取得
curl -s http://localhost:8000/workflows/{wf_id}
# ノード追加
curl -s http://localhost:8000/workflows/{wf_id}/nodes -X POST -H 'Content-Type: application/json' -d '{"node_type":"generative_ai","config":{"prompt":"Summarize"}}'
# 実行
curl -s http://localhost:8000/workflows/{wf_id}/run
```

## API リファレンス
- POST `/workflows` → `{ id, name }`
- GET `/workflows/{id}` → `{ id, name, nodes[] }`
- POST `/workflows/{id}/nodes` → `{ message, node_id }`
- POST `/workflows/{id}/run` → `{ final_output }`

## CORS とポート
- バックエンドは `http://localhost:3000` を許可
- ポート競合時はポートと CORS 設定を合わせて変更

## 仕様生成（specify）
リポジトリルートで：
```bash
./.specify/scripts/bash/create-new-feature.sh --json '{"feature_name":"Workflow Builder sample app for assignment", "...": "..."}'
```
このスクリプトは：
- 新しいブランチを作成してチェックアウト（例：`001-feature-name-workflow`）
- `specs/001-feature-name-workflow/spec.md` に仕様ファイルを初期化
- テンプレートは `.specify/templates/spec-template.md`

## Docker（開発、ホットリロード/HMR）
```bash
# リポジトリルート
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```
開発 compose はソースをマウントし、バックエンドは reload、フロントエンドは HMR を有効化します。

## 静的ホスティング
```bash
cd client
VITE_API_BASE=https://api.example.com npm run build
# client/dist を任意の静的ホスティングにアップロード
```
`VITE_API_BASE` を設定しない場合、フロントエンドはデフォルトで `http://localhost:8000` を使用します。

## トラブルシューティング
- フロントが真っ白/起動失敗：
  - `client/index.html` に `<div id="root"></div>` と `/src/main.tsx` エントリがあるか確認
  - `client/src/main.tsx` が `<App />` を `#root` にレンダーしているか確認
  - 依存変更時は `npm install` を再実行
- バックエンド応答なし：
  - Uvicorn が 8000 番で稼働しているか確認
  - ターミナルに FastAPI 起動とルート登録のログがあるか確認
- CORS エラー：
  - `server/main.py` の許可オリジンに `http://localhost:3000` が含まれているか確認

## ライセンス
課題用途のみ。

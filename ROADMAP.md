# Discord通知MCP 開発ロードマップ

## 概要
Claude Code / Claude Desktop等のMCPクライアントから呼び出せる、
Discord通知用のMCPサーバーをPythonで実装する。

---

## Phase 0: 要件・設計の確定
- [x] 通知経路の選定
  - **Webhook方式に確定**(管理コストの低さを優先し、Bot Token方式は不採用)
  - チャンネルごとにWebhook URLを発行し、`{チャンネル名: URL}` の形で設定管理する
  - 対象チャンネルが増える場合は都度Webhookを手動発行する運用とする
- [x] 提供するMCPツールの洗い出し（例）
  - `send_notification(channel: str, message: str)` : テキスト通知(いったんこれのみ実装)
- [x] 認証情報の管理方法
  - 命名規則: `DISCORD_WEBHOOK_<チャンネル名>` で `.env` に複数登録(例: `DISCORD_WEBHOOK_GENERAL`, `DISCORD_WEBHOOK_ALERT`)
  - `config.py` が起動時に `python-dotenv` で読み込み、プレフィックスを剥がして `{チャンネル名: URL}` の辞書を生成し、MCPツールの `channel` 引数と対応させる
  - `pydantic` でWebhook URLの形式を検証し、1件も設定されていない場合は起動時にエラーとする
  - `.env` は `.gitignore` に必ず含め、コミットしない。代わりに値を空にした `.env.example` をコミットしてセットアップ手順とする
  - ログ・エラーメッセージ・MCPツールのレスポンスにWebhook URLを含めない(送信成否とチャンネル名のみ返す)
- [x] MCPのトランスポート方式 → **stdio方式に確定**(ローカルのClaude Desktop/Claude Code統合が主用途のため。ネットワーク経由の認証・ホスティングが不要)
  - 将来検討（優先度低・未着手）: 複数人/リモート共有が必要になった場合のStreamable HTTP対応

---

## Phase 1: 開発環境構築
- [x] Python venv作成（Windows 11 / PowerShell前提） → `.venv` 作成済み(Python 3.14.7)
- [ ] 依存パッケージ選定
  - `mcp`（公式Python SDK）
  - `httpx`（Discord Webhook/API呼び出し用、非同期対応）
  - `python-dotenv`
  - `pydantic`（入力バリデーション）
- [ ] `pyproject.toml` によるパッケージ構成
- [ ] Git初期化・`.gitignore` 整備（`.env`, `__pycache__` 等）
- [ ] Lintツール導入（PEP8準拠のため `ruff` or `flake8` + `black`）

---

## Phase 2: 最小実装（MVP）
- [ ] Webhook経由でテキストメッセージを送信する単一ツールを実装
- [ ] MCPサーバーの起動・ツール登録の最小骨格作成
- [ ] `mcp dev` / MCP Inspector で単体動作確認
- [ ] Claude Desktop / Claude Codeの設定ファイルに登録し、実際に通知が飛ぶことを確認

---

## Phase 3: 機能拡張
- [ ] 通知先の切り替え対応（複数Webhookを設定で選択、チャンネル追加時は`.env`にURLを追記するだけで対応）
- 将来検討（優先度低・未着手）: Embed通知対応、ファイル添付対応

---

## Phase 4: 堅牢性の向上
- [ ] エラーハンドリング（Discord API側のレート制限・タイムアウト対応）
- [ ] リトライ処理（指数バックオフ）
- [ ] ロギング整備（送信成否・失敗理由を記録）
- [ ] 入力バリデーション強化（メッセージ長制限2000文字対応等）

---

## Phase 5: テスト・品質保証
- [ ] `pytest` によるユニットテスト整備
  - Discord API呼び出し部分は `respx` 等でモック化
- [ ] 単一責任の原則に沿ったモジュール分割の見直し
  - 例: `discord_client.py`（送信処理）/ `tools.py`（MCPツール定義）/ `config.py`（設定読込）
- [ ] 各処理へのコメント付与（CLAUDE.mdルール準拠）

---

## Phase 6: 配布・運用整備
- [ ] README作成（セットアップ手順、Claude Desktop/Codeへの登録方法）
- [ ] Docker化（必要な場合、WSL内Dockerを使用する前提で `Dockerfile` / `docker-compose.yml` 作成）
- [ ] バージョニング・CHANGELOG整備
- [ ] （任意）PyPI公開 or GitHub Releasesでの配布

---

## 想定ディレクトリ構成（例）
```
notification_mcp/
├── CLAUDE.md
├── ROADMAP.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── src/
│   └── notification_mcp/
│       ├── __init__.py
│       ├── server.py        # MCPサーバーのエントリポイント
│       ├── tools.py         # MCPツール定義
│       ├── discord_client.py # Discord送信処理
│       └── config.py        # 設定読込・バリデーション
└── tests/
    ├── test_tools.py
    └── test_discord_client.py
```

---

## 次のアクション
1. Phase 0の残項目（MCPツール定義・.env設計）を確定
2. Phase 1の環境構築から着手
3. MVP（Phase 2）を最短で動かし、以降は段階的に拡張

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
- [x] 依存パッケージ選定 → `.venv` にインストール済み
  - `mcp`（公式Python SDK / 2.2.0）
  - `httpx`（Discord Webhook呼び出し用、非同期対応 / 0.28.1）
  - `python-dotenv`（1.2.3）
  - `pydantic`（入力バリデーション / 2.13.5）
- [x] `pyproject.toml` によるパッケージ構成 → 作成済み(ビルドバックエンド: hatchling、`src`レイアウト、`notification-mcp`コマンドを`[project.scripts]`で定義)。`pip install -e .` で動作確認済み
- [x] Git初期化・`.gitignore` 整備（`.env`, `__pycache__` 等） → 初期化済み・`.gitignore`に`.venv/`, `__pycache__/`, `*.pyc`, `.env`, `.pytest_cache/`, `*.egg-info/`を登録済み
- [x] Lintツール導入（PEP8準拠のため `ruff` or `flake8` + `black`） → `ruff`を採用(0.16.8)。`pyproject.toml`の`[project.optional-dependencies].dev`と`[tool.ruff]`に設定を追加し、`ruff check`で動作確認済み

---

## Phase 2: 最小実装（MVP）
- [x] Webhook経由でテキストメッセージを送信する単一ツールを実装(関数単位)
  - [x] `config.py` : `load_webhook_config() -> dict[str, str]` — `.env`から`DISCORD_WEBHOOK_<チャンネル名>`を読み込み、`{チャンネル名: URL}`の辞書を返す
  - [x] `config.py` : `validate_webhook_url(url: str) -> None` — Webhook URLの形式を検証し、不正なら例外を送出する
  - [x] `discord_client.py` : `send_webhook_message(webhook_url: str, message: str) -> None` — httpxでWebhookにテキストメッセージを非同期送信する
  - [x] `tools.py` : `send_notification(channel: str, message: str) -> str` — チャンネル名からWebhook URLを解決し送信、結果メッセージを返すMCPツール本体
- [x] MCPサーバーの起動・ツール登録の最小骨格作成
  - [x] `server.py` : `main() -> None` — `MCPServer`を初期化し`send_notification`を`add_tool`で登録、stdioで起動するエントリポイント
- [x] `mcp dev` / MCP Inspector で単体動作確認 → `mcp dev`はブラウザ操作が必要なため、代わりにstdioクライアントを使った検証スクリプトで確認(`list_tools`でのスキーマ確認、未設定チャンネル時のエラー、送信失敗時のHTTPエラー捕捉が正常動作することを確認済み)
- [ ] Claude Desktop / Claude Codeの設定ファイルに登録し、実際に通知が飛ぶことを確認 → **保留**(利用予定クライアントの登録方法が未確定のため後日実施)

---

## Phase 3: 機能拡張
- [ ] 通知先の切り替え対応（複数Webhookを設定で選択、チャンネル追加時は`.env`にURLを追記するだけで対応）
- 将来検討（優先度低・未着手）: Embed通知対応、ファイル添付対応

---

## Phase 4: 堅牢性の向上
- [x] 入力バリデーション強化（メッセージ長制限2000文字対応等） → Phase 2で実装済み(`discord_client.py`の`send_webhook_message`内でチェック)
- [x] タイムアウト対応(関数単位)
  - [x] `discord_client.py` : `send_webhook_message(webhook_url: str, message: str, timeout: float = 10.0) -> None` — 既存関数にタイムアウト引数を追加し、httpxのタイムアウト設定に反映する
- [x] リトライ処理(指数バックオフ、関数単位)
  - [x] `discord_client.py` : `send_webhook_message_with_retry(webhook_url: str, message: str, max_retries: int = 3) -> None` — `send_webhook_message`を指数バックオフでリトライし、429(レート制限)時は`Retry-After`ヘッダーを尊重する。リトライ対象は429/5xxのみ(4xxは即エラー)
  - [x] `tools.py` : `send_notification`が`send_webhook_message`ではなく`send_webhook_message_with_retry`を呼ぶように修正 → 実チャンネルへの送信で動作確認済み
- [x] ロギング整備(関数単位)
  - [x] `logging_config.py` : `setup_logging() -> None` — ロギングのフォーマット・出力先を初期化する(標準エラー出力と`log/notification_mcp.log`の両方に出力)。`httpx`/`httpcore`のログにWebhook URLが漏洩する問題を発見し、WARNING以上に制限して対処。`log/*.log`は`.gitignore`に追加(`.gitkeep`のみ追跡)
  - [x] `server.py` : `main()`の冒頭で`setup_logging()`を呼び出す
  - [x] `tools.py` : `send_notification`内で送信成否をログ出力するように修正 → 動作確認済み(標準出力を汚さず、URLも記録されないことを確認)
  - [x] 追加修正: `validate_webhook_url`の例外メッセージからURL本体を除去、`load_webhook_config()`呼び出しを`try/except`で保護(不正URL時にMCP SDKのクラッシュログ経由でURLが漏洩する経路を遮断)

---

## Phase 5: テスト・品質保証
- [x] `pytest` によるユニットテスト整備(関数単位、Discord API呼び出しは`respx`でモック化) → 12件全て成功。`pytest`/`pytest-asyncio`/`respx`を開発依存に追加、`pyproject.toml`に`[tool.pytest.ini_options]`設定を追加
  - [x] `tests/test_config.py` : `test_validate_webhook_url_accepts_valid_url`
  - [x] `tests/test_config.py` : `test_validate_webhook_url_rejects_invalid_url`
  - [x] `tests/test_config.py` : `test_load_webhook_config_returns_channel_url_dict` → `load_dotenv()`が呼び出し元ディレクトリを起点に親をたどって実プロジェクトの`.env`を見つけてしまう仕様を発見し、テストでは`load_dotenv`をno-op化して分離
  - [x] `tests/test_config.py` : `test_load_webhook_config_raises_when_no_webhooks_configured`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_posts_content_successfully`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_raises_when_message_too_long`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_with_retry_succeeds_after_retryable_error`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_with_retry_raises_on_non_retryable_error`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_with_retry_raises_after_max_retries`
  - [x] `tests/test_tools.py` : `test_send_notification_returns_success_message`
  - [x] `tests/test_tools.py` : `test_send_notification_returns_error_for_unknown_channel`
  - [x] `tests/test_tools.py` : `test_send_notification_returns_error_on_http_failure` → Webhook URLが結果に含まれないことも確認
- [x] 単一責任の原則に沿ったモジュール分割の見直し → `config.py`/`discord_client.py`/`logging_config.py`/`server.py`はそれぞれ単一の関心事に閉じており問題なし。`tools.py`の`send_notification`はMCPツール境界層として複数処理(設定解決・送信・エラー変換・ログ)を担うが、境界層の責務として妥当と判断
  - 追加対応: `discord_client.py`の`send_webhook_message_with_retry`にリトライ時のログ出力(`logger.warning`)を追加(Webhook URLが含まれないことを確認済み)
- [x] 各処理へのコメント付与（CLAUDE.mdルール準拠） → 全5ファイルをレビューし、コメントが不足していた6箇所(メッセージ長チェック、リトライ判定、`.env`フィルタリング、チャンネル解決、送信処理、`server.py`の各ステップ)に追加。Lint・動作確認済み

---

## Phase 6: 配布・運用整備
- [x] README作成（セットアップ手順、Claude Desktop/Codeへの登録方法） → 作成済み。記載のLint/テストコマンドの動作も確認済み
- [x] バージョニング・CHANGELOG整備 → Semantic Versioningを採用(`pyproject.toml`の`version = "0.1.0"`と一致)。`CHANGELOG.md`をKeep a Changelog形式で作成し、READMEからリンク
- ~~Docker化~~ → 不要と判断(個人のローカル利用が主目的のため)
- ~~（任意）PyPI公開 or GitHub Releasesでの配布~~ → 不要と判断

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

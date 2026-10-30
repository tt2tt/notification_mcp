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
- [x] Claude Desktop / Claude Codeの設定ファイルに登録し、実際に通知が飛ぶことを確認 → 別PCにてリリース済み(実際の通知送信を確認済み)

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

## Phase 7: CLIエントリポイントの追加
AI(MCPクライアント)以外のプログラムやバッチ・タスクスケジューラーから、
`.venv\Scripts\python.exe -m notification_mcp.cli --channel <チャンネル名> --message <本文>` の形で通知を送信できるようにする。
送信処理はサービス層(`notifier.notify`)に切り出してMCPツールとCLIで共有し、MCP経由と同じ挙動(リトライ・ログ・URL非出力)を保つ。
例外処理はデコレータ(`error_handlers.py`)に統一する。

- [x] 送信処理のサービス層への切り出し(成否をMCP用の文字列ではなく例外で判定できるようにする) (`feature/notifier-service`)
  - [x] `exceptions.py` : `NotificationError`系の例外クラス — 基底`NotificationError`(ログレベルを属性で保持)と、`WebhookConfigError`/`ChannelNotConfiguredError`/`MessageRejectedError`/`SendFailedError`を定義する。メッセージは日本語でWebhook URLを含めない
  - [x] `error_handlers.py` : `reraise_as(target, *sources)` — 指定した例外を`target`へ変換して再送出する汎用デコレータ
  - [x] `error_handlers.py` : `translate_send_errors(func)` — 送信関数の`httpx`例外・文字数超過の`ValueError`を、チャンネル名入りの`SendFailedError`/`MessageRejectedError`へ変換するデコレータ
  - [x] `notifier.py` : `_load_webhook_config() -> dict[str, str]` — `load_webhook_config`を呼び、設定エラーを`WebhookConfigError`へ変換する(`reraise_as`を適用)
  - [x] `notifier.py` : `_resolve_webhook_url(webhook_config, channel) -> str` — チャンネル名からWebhook URLを解決し、未設定なら`ChannelNotConfiguredError`を送出する
  - [x] `notifier.py` : `_send(channel, webhook_url, message) -> None` — リトライ付きで送信する(`translate_send_errors`を適用)
  - [x] `notifier.py` : `notify(channel: str, message: str) -> None` — 設定読込・URL解決・送信を順に行い、成功をログ出力する
  - [x] `error_handlers.py` : `return_error_message(func)` — `NotificationError`をログ出力し、`"エラー: ..."`の文字列を返すMCPツール用デコレータ
  - [x] `tools.py` : `send_notification`を`notify`呼び出しと成功メッセージ返却のみの境界層に修正(`return_error_message`を適用)。`tests/test_tools.py`のモック対象も`notifier`へ変更する
  - レビュー指摘対応(1回目)
    - [x] `discord_client.py` : `_resolve_wait_seconds` — 数値以外の`Retry-After`(HTTP日付形式等)は`ValueError`を出さず指数バックオフへフォールバックする(入力エラーへの誤分類を防止)
    - [x] `error_handlers.py` : `translate_send_errors` — `httpx.InvalidURL`も`SendFailedError`へ変換し、例外連鎖を`from None`で切ってトレースバック経由のWebhook URL漏洩を防ぐ
    - [x] `notifier.py` : `_resolve_webhook_url` — 戻り値の処理にコメントを追加
    - [x] `notifier.py` : `notify` — 成功ログ出力にコメントを追加
  - レビュー指摘対応(2回目)
    - [x] `discord_client.py` : `_resolve_wait_seconds` — 待機秒数に上限(60秒)を設け、巨大な`Retry-After`による長時間停止・`inf`による無限待機を防ぐ
    - [x] `error_handlers.py` : `reraise_as` — 例外連鎖を`from None`で切る方針に統一し、戻り値処理にコメントを追加
    - [x] `error_handlers.py` : `translate_send_errors` — 戻り値処理にコメントを追加
    - [x] `error_handlers.py` : `return_error_message` — 想定外の例外も汎用メッセージへ変換し(例外の型名のみログ出力)、URLを含み得る例外文字列がMCPクライアントへ渡らないようにする
  - レビュー指摘対応(3回目、ユーザー判断により案Aを採用)
    - [x] `discord_client.py` : `send_webhook_message_with_retry` — 待機秒数が上限(60秒)を超える場合はリトライせず即座に例外を送出する(早すぎる再送・長時間ブロック・重複通知を防ぐ)
    - [x] `discord_client.py` : `_resolve_wait_seconds` — 上限への丸めを廃止し、サーバー指示どおりの待機秒数を返す(上限判定は呼び出し側で行う)
- [x] CLIの実装 (`feature/cli`)
  - [x] `error_handlers.py` : `_log_failure(error: Exception) -> None` — 失敗時のログ出力を共通化する(`NotificationError`は例外ごとのログレベルとメッセージ、想定外の例外は型名のみ)
  - [x] `error_handlers.py` : `return_error_message` — ログ出力を`_log_failure`へ置き換える
  - [x] `error_handlers.py` : `return_exit_code(func)` — 例外を`_log_failure`でログ出力し、終了コード1を返すCLI用デコレータ(想定外の例外も含む)
  - [x] `cli.py` : `parse_args(argv: list[str] | None = None) -> argparse.Namespace` — `--channel`/`--message`(いずれも必須)を解析する
  - [x] `cli.py` : `main(argv: list[str] | None = None) -> int` — ロギングを初期化して`notify`を実行する。終了コードは成功時0・失敗時1(`return_exit_code`を適用)
  - レビュー指摘対応(1回目)
    - [x] `cli.py` : `parse_args` — `-`で始まるメッセージは`--message=...`形式で渡す必要がある旨をヘルプに明記する
    - [x] `discord_client.py` : `send_webhook_message` — `allowed_mentions`を空にして本文中の`@everyone`/`@here`等によるメンション通知を無効化する(`tests/test_discord_client.py`の送信ボディ検証も更新)
  - レビュー指摘対応(2回目)
    - [x] `discord_client.py` : `send_webhook_message` — `allowed_mentions`を`{"parse": ["users", "roles"]}`とし、`@everyone`/`@here`のみ無効化して個別ユーザー・ロールへのメンション(`<@id>`/`<@&id>`)は従来どおり通知する
  - レビュー指摘対応(3回目、ユーザー判断により案Aを採用)
    - [x] `exceptions.py` : `InvalidChannelError` — チャンネル名の形式が不正であることを表す例外(WARNING扱い、メッセージに入力値を含めない)を追加する
    - [x] `notifier.py` : `_validate_channel(channel: str) -> None` — チャンネル名が英数字・`_`・`-`のみで構成されているか検証し、不正なら`InvalidChannelError`を送出する(改行等によるログインジェクションを防ぐ)
    - [x] `notifier.py` : `notify` — 設定読込より前に`_validate_channel`を呼び出す
- [x] テスト追加(Discord API呼び出しはモック化) (`test/notifier-cli`)
  - [x] `tests/test_error_handlers.py` : `test_reraise_as_converts_exception`
  - [x] `tests/test_error_handlers.py` : `test_translate_send_errors_converts_http_status_error`
  - [x] `tests/test_error_handlers.py` : `test_return_error_message_returns_prefixed_message`
  - [x] `tests/test_error_handlers.py` : `test_return_exit_code_returns_one_on_error`
  - [x] `tests/test_discord_client.py` : `test_send_webhook_message_with_retry_gives_up_when_retry_after_too_long`
  - [x] `tests/test_notifier.py` : `test_notify_sends_message_successfully`
  - [x] `tests/test_notifier.py` : `test_notify_raises_for_unknown_channel`
  - [x] `tests/test_notifier.py` : `test_notify_raises_webhook_config_error`
  - [x] `tests/test_notifier.py` : `test_notify_raises_for_invalid_channel_name`
  - [x] `tests/test_cli.py` : `test_parse_args_returns_channel_and_message`
  - [x] `tests/test_cli.py` : `test_main_returns_zero_on_success`
  - [x] `tests/test_cli.py` : `test_main_returns_one_on_failure`
  - レビュー指摘対応(1回目)
    - [x] `tests/test_error_handlers.py` : `test_reraise_as_converts_exception` — `__cause__ is None`も検証し、例外連鎖が切れていることを確実に確認する
    - [x] `tests/test_error_handlers.py` : `test_translate_send_errors_converts_http_status_error` — 例外連鎖が切れていること(`__cause__ is None`/`__suppress_context__`)を検証する
    - [x] `tests/test_discord_client.py` : `test_send_webhook_message_with_retry_gives_up_when_retry_after_too_long` — `asyncio.sleep`をモック化して待機しないことを検証し、関数呼び出しのネストを解消する
- [x] ドキュメント更新 (`docs/cli-usage`)
  - [x] `README.md` : CLIの使い方(絶対パスでの実行例、終了コード)とディレクトリ構成を追記
  - [x] `CHANGELOG.md` : CLI追加をUnreleasedに追記(リリース時に`0.2.0`へ)
  - レビュー指摘対応(1回目)
    - [x] `discord_client.py` : モジュール読込時に`httpx`/`httpcore`のログをWARNING以上に制限する(`setup_logging`を呼ばない直接呼び出しでもWebhook URLがログに出ないようにする)
    - [x] `logging_config.py` : `setup_logging` — `discord_client`へ移した`httpx`/`httpcore`のログ抑制処理を削除する(重複の解消)
    - [x] `README.md` : チャンネル名は小文字で指定する旨・不正なチャンネル名は終了コード1になる旨・直接呼び出し時の例外範囲とログ出力先・通常インストール時の挙動・`-`始まり本文の例・ディレクトリ構成を実態に合わせて修正する
    - [x] `CHANGELOG.md` : Keep a Changelogにない「確認済み」区分を削除する
  - レビュー指摘対応(2回目)
    - [x] `discord_client.py` : `_WebhookUrlRedactingFilter` — ログレコード中のWebhook URLの`id/token`部分を伏せ字に置き換える`logging.Filter`を追加する
    - [x] `discord_client.py` : `_install_log_redaction() -> None` — `httpx`ロガーへ伏せ字フィルターを登録する(ログレベル変更による抑制を廃止し、呼び出し側のログ設定を変えないようにする)
    - [x] `tests/test_discord_client.py` : `test_httpx_request_log_redacts_webhook_url` — `httpx`をINFOにしてもログにWebhookトークンが出力されないことを検証する
    - [x] `README.md` : 直接呼び出し時のログの説明を伏せ字方式に合わせて修正する
    - [x] `CHANGELOG.md` : Security項目を伏せ字方式に合わせて修正する

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

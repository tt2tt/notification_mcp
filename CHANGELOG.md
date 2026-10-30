# Changelog

このプロジェクトの変更履歴を記録します。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

`0.x`系のあいだはマイナーバージョンの更新でも破壊的変更を含む場合があります。

## [Unreleased]

リリース時に`0.2.0`として公開予定。

### Added
- コマンドラインから通知を送信するCLI `python -m notification_mcp.cli --channel <チャンネル名> --message <本文>` を追加(終了コード: 成功0・送信失敗1・引数不正2)
- 通知送信のサービス層 `notifier.notify(channel, message)` を追加し、MCPツールとCLIで共有(失敗時は`NotificationError`系の例外を送出)
- 通知処理の例外クラス(`exceptions.py`)と、例外処理を共通化するデコレータ(`error_handlers.py`)を追加
- `error_handlers`/`notifier`/`cli`のユニットテストを追加

### Changed
- 本文中の`@everyone`/`@here`による全員宛てのメンション通知を無効化(個別ユーザー・ロールへのメンションは従来どおり通知)
- `Retry-After`の指示が60秒を超える場合は、リトライせずに送信失敗として扱うよう変更
- チャンネル名に使える文字を英数字・`_`・`-`に限定
- 運用するチャンネルを`general`から`news`へ変更し、`fx`を追加(`.env.example`のキーを`DISCORD_WEBHOOK_NEWS`/`DISCORD_WEBHOOK_FX`/`DISCORD_WEBHOOK_ALERT`に更新)。`channel="general"`を指定している呼び出しは`news`への変更が必要
- チャンネル名の大文字・小文字を区別しないよう変更(`NEWS`でも`news`へ送信)
- 値が空・URL形式が不正・チャンネル名が不正な`DISCORD_WEBHOOK_`系のキーは、全体をエラーにせず警告ログを出して読み飛ばすよう変更
- `DISCORD_WEBHOOK_`系の設定を送信のたびに`.env`から読み直し、MCPサーバーを再起動せずに変更が反映されるよう変更(OS環境変数が優先。Webhook以外の設定は従来どおり既存の環境変数を上書きしない)
- Webhook URLの形式チェックを全体一致とし、トークンはURLセーフな文字(英数字・`_`・`-`)のみ、末尾は`/`1つとクエリのみ許可

### Fixed
- HTTP日付形式など秒数以外の`Retry-After`ヘッダーで、入力エラーと誤って判定される問題を修正(指数バックオフで待機)
- `.env`の1つのキーの値が空なだけで、すべてのチャンネルへ送信できなくなる問題を修正
- `.env`の小文字のキー(`discord_webhook_news`等)が読み込まれない場合がある問題を修正

### Security
- MCPツール・CLIにおいて、想定外の例外・`httpx.InvalidURL`・例外連鎖(トレースバック)を経由してWebhook URLが出力される経路を遮断
- `httpx`のリクエストログに含まれるWebhook URL(バージョン付きパスを含む)のID・トークン部分を伏せ字にするフィルターを送信モジュールに追加し、`notify`を直接呼び出す場合や呼び出し側がログレベルを変更した場合もトークンが出力されないよう修正(MCPサーバー・CLIでは従来どおり`httpx`/`httpcore`のログをWARNING以上に制限)
- 改行等を含むチャンネル名によるログインジェクションを防止

## [0.1.0] - 2026-09-23

### Added
- Discord Webhookへテキスト通知を送信するMCPツール `send_notification(channel, message)` を実装
- `.env`による複数チャンネル分のWebhook URL管理(`DISCORD_WEBHOOK_<チャンネル名>`)
- タイムアウト対応・指数バックオフによるリトライ処理(429時は`Retry-After`ヘッダーを尊重)
- 標準エラー出力および`log/notification_mcp.log`へのロギング(Webhook URLが記録されないよう対策済み)
- `pytest`によるユニットテスト一式(`config`/`discord_client`/`tools`)
- `ruff`によるLint設定、`pyproject.toml`によるパッケージ構成
- README・ROADMAPの整備

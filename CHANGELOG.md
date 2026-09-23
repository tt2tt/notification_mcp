# Changelog

このプロジェクトの変更履歴を記録します。
フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準拠します。

`0.x`系のあいだはマイナーバージョンの更新でも破壊的変更を含む場合があります。

## [Unreleased]

### 未着手
- Claude Desktop / Claude Codeへの実登録・動作確認(利用クライアント確定後に実施予定)

## [0.1.0] - 2026-09-23

### Added
- Discord Webhookへテキスト通知を送信するMCPツール `send_notification(channel, message)` を実装
- `.env`による複数チャンネル分のWebhook URL管理(`DISCORD_WEBHOOK_<チャンネル名>`)
- タイムアウト対応・指数バックオフによるリトライ処理(429時は`Retry-After`ヘッダーを尊重)
- 標準エラー出力および`log/notification_mcp.log`へのロギング(Webhook URLが記録されないよう対策済み)
- `pytest`によるユニットテスト一式(`config`/`discord_client`/`tools`)
- `ruff`によるLint設定、`pyproject.toml`によるパッケージ構成
- README・ROADMAPの整備

# notification-mcp

Discord Webhookへ通知を送信するMCP(Model Context Protocol)サーバーです。
Claude Desktop / Claude Codeなど、MCP対応クライアントからDiscordへテキスト通知を送信できます。

バージョニングは[Semantic Versioning](https://semver.org/lang/ja/)に準拠します。変更履歴は[CHANGELOG.md](CHANGELOG.md)を参照してください。

## 必要要件

- Windows 11
- Python 3.11以上
- 通知先チャンネルに設定したDiscord Webhook URL

## セットアップ

### 1. 仮想環境の作成

PowerShellで以下を実行します。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. 依存パッケージのインストール

開発用パッケージ（`ruff`, `pytest`, `mcp[cli]`等）を含めてインストールします。

```powershell
pip install -e ".[dev]"
```

### 3. Webhook URLの設定

`.env.example`を`.env`にコピーし、Discordで発行したWebhook URLを設定します。

```powershell
copy .env.example .env
```

`.env`の命名規則は `DISCORD_WEBHOOK_<チャンネル名>` です。チャンネル名は小文字化されて、MCPツールの`channel`引数と対応します。

```
DISCORD_WEBHOOK_GENERAL=https://discord.com/api/webhooks/xxxx/xxxx
DISCORD_WEBHOOK_ALERT=https://discord.com/api/webhooks/yyyy/yyyy
```

上記の場合、`channel="general"` または `channel="alert"` で送信先を指定できます。

`.env`にはトークンを含む機密情報が入るため、**絶対にコミットしないでください**（`.gitignore`で除外済みです）。

## 提供ツール

| ツール名 | 引数 | 説明 |
|---|---|---|
| `send_notification` | `channel: str`, `message: str` | 指定チャンネルのWebhookへテキスト通知を送信する |

- `channel` に使えるのは英数字・`_`・`-` のみです(それ以外を含む場合はエラーになります)。
- 本文中の `@everyone` / `@here` による全員宛てのメンション通知は無効化されます。個別ユーザー・ロールへのメンション(`<@ユーザーID>` / `<@&ロールID>`)は通知されます。

## Claude Desktop / Claude Codeへの登録

MCP設定ファイルに、本プロジェクトの仮想環境のPythonでサーバーを起動するよう登録します。
登録内容はどちらも同じで、以下のJSONを`mcpServers`に追加します。

```json
{
  "mcpServers": {
    "notification-mcp": {
      "command": "C:\\path\\to\\notification_mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "notification_mcp.server"]
    }
  }
}
```

`C:\path\to\notification_mcp` の部分は、実際にクローン・配置したパスに置き換えてください。

### 登録先ファイル

| クライアント | 設定ファイルのパス |
|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json`(例: `C:\Users\<ユーザー名>\AppData\Roaming\Claude\claude_desktop_config.json`) |
| Claude Code(プロジェクト単位で共有する場合) | プロジェクトルート直下の`.mcp.json` |
| Claude Code(ユーザー単位で登録する場合) | `claude mcp add` コマンドで登録(内部的に`~/.claude.json`に保存される) |

Claude Codeでは、ターミナルから以下のコマンドでも同様の登録ができます。

```powershell
claude mcp add notification-mcp -- C:\path\to\notification_mcp\.venv\Scripts\python.exe -m notification_mcp.server
```

## 動作確認

単体でサーバーを起動する場合は以下を実行します(通常はMCPクライアントがサブプロセスとして起動します)。

```powershell
python -m notification_mcp.server
```

## CLIからの送信

AI(MCPクライアント)を介さず、バッチ・タスクスケジューラー・他のプログラムからも同じ通知処理を呼び出せます。
本プロジェクトの仮想環境のPythonを絶対パスで指定すれば、どのフォルダからでも実行できます。

```powershell
C:\path\to\notification_mcp\.venv\Scripts\python.exe -m notification_mcp.cli --channel general --message "バッチ処理が完了しました"
```

| 引数 | 必須 | 説明 |
|---|---|---|
| `--channel` | ○ | 送信先のチャンネル名(`.env`の`DISCORD_WEBHOOK_<チャンネル名>`に対応) |
| `--message` | ○ | 送信するメッセージ本文(2000文字以内) |

`-` で始まる本文は、オプションと区別するため `--message="--- 完了 ---"` のように `=` でつないで指定してください。

### 終了コード

| 終了コード | 意味 |
|---|---|
| `0` | 送信成功 |
| `1` | 送信失敗(未設定のチャンネル、文字数超過、HTTPエラー、通信エラー等) |
| `2` | 引数の不足・不正 |

バッチファイルでは `if errorlevel 1` 等で成否を判定できます。
処理結果のログはMCPサーバーと同じく、標準エラー出力と `log/notification_mcp.log` に出力されます。

### Pythonから直接呼び出す場合

本プロジェクトの仮想環境で実行するか、呼び出し側の仮想環境に `pip install -e C:\path\to\notification_mcp` でインストールしたうえで、サービス層の `notify` を呼び出します。
失敗時は `notification_mcp.exceptions.NotificationError` 系の例外が送出されます。

```python
import asyncio

from notification_mcp.exceptions import NotificationError
from notification_mcp.notifier import notify

try:
    coroutine = notify("general", "通知メッセージ")
    asyncio.run(coroutine)
except NotificationError as error:
    print(f"送信に失敗しました: {error}")
```

`.env` とログの保存先はパッケージの配置場所を基準に決まるため、`-e` を付けずに通常インストールすると `.env` が見つからない・ログを書き込めない場合があります。

## 開発

### Lint

```powershell
ruff check src tests
```

### テスト

```powershell
pytest
```

### ログ

実行ログは標準エラー出力と `log/notification_mcp.log` の両方に出力されます。
Webhook URL等の機密情報はログに出力されない設計になっています。

## ディレクトリ構成

```
notification_mcp/
├── CLAUDE.md
├── README.md
├── ROADMAP.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── log/
│   └── notification_mcp.log  # 実行時に生成(gitignore対象)
├── src/
│   └── notification_mcp/
│       ├── __init__.py
│       ├── server.py           # MCPサーバーのエントリポイント
│       ├── cli.py              # CLIのエントリポイント
│       ├── tools.py            # MCPツール定義(境界層)
│       ├── notifier.py         # 通知送信のサービス層(MCPツール・CLIで共有)
│       ├── error_handlers.py   # 例外処理を共通化するデコレータ
│       ├── exceptions.py       # 通知処理の例外クラス
│       ├── discord_client.py   # Discord Webhookへの送信・リトライ処理
│       ├── config.py           # 設定読込・バリデーション
│       └── logging_config.py   # ロギング設定
└── tests/
    ├── test_cli.py
    ├── test_config.py
    ├── test_discord_client.py
    ├── test_error_handlers.py
    ├── test_notifier.py
    └── test_tools.py
```

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

- `channel` は `.env` のキー名の `<チャンネル名>` 部分を**小文字**で指定します(例: `DISCORD_WEBHOOK_GENERAL` → `general`)。
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
| `--channel` | ○ | 送信先のチャンネル名。`.env`の`DISCORD_WEBHOOK_<チャンネル名>`の`<チャンネル名>`を小文字で指定(英数字・`_`・`-`のみ) |
| `--message` | ○ | 送信するメッセージ本文(2000文字以内) |

`-` で始まる本文は、オプションと区別するため `--message="-完了"` のように `=` でつないで指定してください。

### 終了コード

| 終了コード | 意味 |
|---|---|
| `0` | 送信成功 |
| `1` | 送信失敗(チャンネル名の形式不正・未設定のチャンネル、文字数超過、HTTPエラー、通信エラー等) |
| `2` | 引数の不足・不明なオプション(argparseによる検出) |

バッチファイルでは `if errorlevel 1` 等で成否を判定できます。
処理結果のログはMCPサーバーと同じく、標準エラー出力と `log/notification_mcp.log` に出力されます。

### Pythonから直接呼び出す場合

本プロジェクトの仮想環境で実行するか、呼び出し側の仮想環境に `pip install -e C:\path\to\notification_mcp` でインストールしたうえで、サービス層の `notify` を呼び出します。
想定される失敗(設定エラー・未設定チャンネル・文字数超過・送信失敗等)は `notification_mcp.exceptions.NotificationError` 系の例外として送出されます。
それ以外の想定外の例外は変換されずにそのまま送出されるため、必要に応じて呼び出し側で捕捉してください(MCPツール・CLIでは境界層のデコレータが捕捉します)。

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

- この呼び出し方では `setup_logging()` が呼ばれないため、`log/notification_mcp.log` には出力されません。ログの出力先は呼び出し側のログ設定に従います(`httpx` のログによるWebhook URLの漏洩は、呼び出し側の設定に関わらず抑制されます)。
- `.env` はパッケージ(`config.py`)の配置場所から親フォルダへ順に探索されます。`-e` を付けずに通常インストールすると、本プロジェクトの `.env` が見つからない、または呼び出し側プロジェクトの別の `.env` を読み込む場合があります。`-e` でのインストールを推奨します。

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
├── README.md
├── CHANGELOG.md
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

"""アプリケーション全体のロギング設定を行うモジュール。"""

import logging
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# プロジェクトルート直下のlogディレクトリにログファイルを出力する
_LOG_DIR = Path(__file__).resolve().parents[2] / "log"
_LOG_FILE = _LOG_DIR / "notification_mcp.log"


def setup_logging(level: int = logging.INFO) -> None:
    """ロギングを初期化する。

    stdioトランスポートは標準出力をプロトコル通信に使うため、
    標準エラー出力と`log`ディレクトリ配下のファイルの両方に出力する。
    """
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
    ]
    # ルートロガーに出力先とフォーマットを設定する
    logging.basicConfig(level=level, format=_LOG_FORMAT, handlers=handlers)

    # 自前の入口(MCPサーバー・CLI)では送信ごとのhttpx/httpcoreの通信ログは不要なため、
    # WARNING以上に制限してログ量を抑える
    # (httpxログ中のWebhook URLは、直接呼び出し時も含め
    #  discord_clientの伏せ字フィルターで保護される)
    for library_logger_name in ("httpx", "httpcore"):
        library_logger = logging.getLogger(library_logger_name)
        library_logger.setLevel(logging.WARNING)

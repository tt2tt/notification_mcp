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
    # (httpx/httpcoreのURL漏洩対策はdiscord_clientのモジュール読込時に行う)
    logging.basicConfig(level=level, format=_LOG_FORMAT, handlers=handlers)

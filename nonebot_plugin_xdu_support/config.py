from pydantic import BaseModel, Extra
from pathlib import Path
from typing import List


class Config(BaseModel, extra=Extra.ignore):
    xdu_support_path: Path = Path()
    go_cqhttp_data_path:Path = Path("./go-cqhttp")
    superusers: List = []
    des_key: str = ""
    sk: str = ""
    appname: str = ""
    asr_api_key: str = None
    asr_secret_key: str = None
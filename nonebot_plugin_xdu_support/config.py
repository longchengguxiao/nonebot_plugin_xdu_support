from pydantic import BaseModel, Extra
from pathlib import Path
from typing import List


class Config(BaseModel, extra=Extra.ignore):
    xdu_support_path: Path = Path()
    superusers: List = []
    des_key: str = ""
    sk: str = ""
    appname: str = ""
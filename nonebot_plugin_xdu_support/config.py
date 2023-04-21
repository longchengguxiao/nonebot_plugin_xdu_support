from pydantic import BaseModel, Extra
from pathlib import Path
from typing import List


class Config(BaseModel, extra=Extra.ignore):
    # 文件储存路径
    xdu_support_path: Path = Path()
    # 语音地址
    go_cqhttp_data_path: Path = Path("./go-cqhttp")
    # 超级用户列表
    superusers: List = []
    # 加密秘钥
    des_key: str = ""
    # 腾讯地图key
    sk: str = ""
    appname: str = ""
    # 腾讯语音识别key
    asr_api_key: str = None
    asr_secret_key: str = None

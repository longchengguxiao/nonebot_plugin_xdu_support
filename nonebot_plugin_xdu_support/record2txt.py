from nonebot.adapters.onebot.v11 import (
    Message,
    Event
)

from datetime import datetime
import httpx
import hashlib
import hmac
import json
import time
import base64
import pilk
import os
import nonebot
from .config import Config

global_config = nonebot.get_driver().config
xdu_config = Config.parse_obj(global_config.dict())
go_cqhttp_data_path = xdu_config.go_cqhttp_data_path

async def type_checker(event: Event) -> str:
    """判断消息类型为语音的规则。

    依赖参数:

    - event: Event 对象
    """
    return event.get_message()[0].type


async def get_text(event: Event, secret_key: str, secret_id: str):
    """通过语音识别获取语音中的文本，仅支持普通话。

    依赖参数:

    - bot: Bot 对象
    - event: Event 对象
    """
    path_amr = os.path.join(go_cqhttp_data_path, "data", "voices" ,event.get_message()[0].data["file"])
    path_pcm = path_amr[0:-4] + ".pcm"
    pilk.decode(path_amr, path_pcm)
    with open(path_pcm, 'rb') as f:
        speech = base64.b64encode(f.read()).decode('utf-8')
    length = os.path.getsize(path_pcm)
    os.remove(path_pcm)
    text = await tencent_get_text(speech, length, secret_key, secret_id)
    return text


async def _get_authorization(params, secret_key: str, secret_id: str):
    service = "asr"
    host = "asr.tencentcloudapi.com"
    algorithm = "TC3-HMAC-SHA256"
    timestamp = int(time.time())
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

    # ************* 步骤 1：拼接规范请求串 *************
    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    ct = "application/json; charset=utf-8"
    payload = json.dumps(params)
    canonical_headers = "content-type:%s\nhost:%s\n" % (ct, host)
    signed_headers = "content-type;host"
    hashed_request_payload = hashlib.sha256(
        payload.encode("utf-8")).hexdigest()
    canonical_request = (http_request_method + "\n" +
                         canonical_uri + "\n" +
                         canonical_querystring + "\n" +
                         canonical_headers + "\n" +
                         signed_headers + "\n" +
                         hashed_request_payload)

    # ************* 步骤 2：拼接待签名字符串 *************
    credential_scope = date + "/" + service + "/" + "tc3_request"
    hashed_canonical_request = hashlib.sha256(
        canonical_request.encode("utf-8")).hexdigest()
    string_to_sign = (algorithm + "\n" +
                      str(timestamp) + "\n" +
                      credential_scope + "\n" +
                      hashed_canonical_request)

    # ************* 步骤 3：计算签名 *************
    # 计算签名摘要函数
    async def _sign(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()
    secret_date = await _sign(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = await _sign(secret_date, service)
    secret_signing = await _sign(secret_service, "tc3_request")
    signature = hmac.new(
        secret_signing,
        string_to_sign.encode("utf-8"),
        hashlib.sha256).hexdigest()

    # ************* 步骤 4：拼接 Authorization *************
    authorization = (
        algorithm +
        " " +
        "Credential=" +
        secret_id +
        "/" +
        credential_scope +
        ", " +
        "SignedHeaders=" +
        signed_headers +
        ", " +
        "Signature=" +
        signature)
    return authorization


async def tencent_get_text(speech, length, secret_key: str, secret_id: str):
    timestamp = int(time.time())
    url = "https://asr.tencentcloudapi.com"
    data = {
        "ProjectId": 0,
        "SubServiceType": 2,
        "EngSerViceType": "16k_zh",
        "SourceType": 1,
        "VoiceFormat": "pcm",
        "UsrAudioKey": "github.com/itsevin",
        "Data": speech,
        "DataLen": length
    }
    headers = {
        "Authorization": await _get_authorization(data, secret_key, secret_id),
        "Content-Type": "application/json; charset=utf-8",
        "Host": "asr.tencentcloudapi.com",
        "X-TC-Action": "SentenceRecognition",
        "X-TC-Version": "2019-06-14",
        "X-TC-Timestamp": str(timestamp),
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=data)
        text = json.loads(resp.text)["Response"]["Result"]
    return text


def record_tts(pattern: str):
    """获取字符串转换的语音的Message对象。
    调用的TX的接口，采用的音源与登录账号的性别有关

    参数:
        pattern: 要进行转换的字符串
    """
    return Message("[CQ:tts,text=" + pattern + "]")

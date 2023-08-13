import requests
from os.path import dirname
from nonebot import logger
"""
【依赖】需要ddddocr>=1.4.7  无需libxduauth
【使用】可以直接使用check_energy函数
"""


def get_capture():
    """
    向url发get请求，获得验证码的gif图片，通过ddddocr识别。并从返回头获得set-cookie参数
    :return: 验证码，sessionId
    """
    # 验证码
    url = 'http://10.168.55.50:8088/searchWeb/DrawHandler.ashx'

    header = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
    }
    from ddddocr import DdddOcr
    ocr = DdddOcr()

    result = requests.get(url, header)
    img_bytes = result.content

    res = ocr.classification(img_bytes)
    # print('识别出的验证码为：' + res)

    headers = str(result.headers).replace("'", '"')
    # print(headers)

    import json
    headers_dict = json.loads(headers)
    set_cookie1 = headers_dict["Set-Cookie"]

    set_cookie2 = set_cookie1.replace("; path=/; HttpOnly", "")

    #     验证码，sessionId
    return res, set_cookie2


def login(webName, webPass, capture_, cookie):
    """
    headers很重要，格式不能缺少。传参是字符串格式
    :param capture_: 验证码
    :param cookie: SessionId
    :return: 状态：“1”表示登录成功
    """
    header = {
        "Cookie": cookie,
        "Ajaxpro-Method": "getLoginInput",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
    }

    url = "http://10.168.55.50:8088/ajaxpro/SearchWeb_Login,App_Web_qbjc33bv.ashx"

    msg = '{"webName": "' + webName + '", "webPass": "' + webPass + '", "yanzh": "' + capture_ + '"}'
    res2 = requests.post(url, headers=header, data=msg)
    # print("status:", res2.text)

    return res2.text


def get_balance(cookie):
    """
    带上cookie发get就行
    :param cookie: SessionId
    :return: 获取到的含有目标数据的网页文本
    """
    url = 'http://10.168.55.50:8088/searchWeb/webFrm/met.aspx'
    header = {
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.66 Safari/537.36 Edg/103.0.1264.44",
    }

    result = requests.get(url, headers=header)

    # res_path = dirname(__file__) + "/res"
    # with open(res_path + "/gethtml.html", "wb") as h:
    #     h.write(result.content)
    # # print("保存成功")
    # logger.success("保存成功")

    return result.content.decode('utf-8')


def get_data(text):
    """
    解析从get_balance获得的含有目标数据的网页
    :param text: 网页
    :return: 宿舍六个表的数据，类型:字典。 每个元素值为列表：分别表示：【表名称，表类型，量程，负荷，剩余量，安装位置】
    """
    import re
    tab = re.compile(r'<td>(.*?)</td>')
    match_lst = re.findall(tab, text)
    # 0 - 41
    date_dic = {}
    for i in range(0, len(match_lst), 7):
        date_dic[str(int(i / 7) + 1)] = match_lst[i:i + 7]
    # print(date_dic)
    return date_dic, int(len(match_lst) / 7)


def is_wright_energy(user: str, passwd: str) -> bool:
    """
    判断账号长度
    """
    return len(user) == 10


def check_energy(name, key):
    """
    外部调用该函数即可，返回值为剩余电量(float)
    """
    name = name
    # 电费账号
    key = key
    # 密码
    logger.info("电费账号：" + name)
    capture, set_cookie = get_capture()
    login(name, key, capture, set_cookie)
    html = get_balance(set_cookie)
    data, num = get_data(html)
    logger.info("共获得：" + str(num) + "条数据")
    # print(data)
    try:
        logger.info("剩余电费：" + str(data[str(num)][-2]) + "度")
        res = data[str(num)][-2]
    except:
        res = -1
        logger.error("出错了，请重试")

    return float(res)


if __name__ == '__main__':
    check_energy("2004140402", "123456")

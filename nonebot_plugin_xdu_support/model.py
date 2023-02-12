import asyncio
import time
import pytz
import datetime
import requests
from libxduauth import EhallSession, SportsSession
import json
from datetime import datetime, timedelta
from typing import List, Dict, Union, Tuple
from pathlib import Path
import os
from .data_source import questions_multi, questions_single
import random
from nonebot.adapters.onebot.v11 import Message
from pyDes import des, CBC, PAD_PKCS5
import binascii
from requests.cookies import RequestsCookieJar
import httpx
from collections import Counter
from dateutil.parser import parse
import numpy as np
import hashlib

# 晨午晚检------------------------------------------------------------------------


def commit_data(username: str, password: str) -> str:
    sess = requests.session()
    sess.post(
        'https://xxcapp.xidian.edu.cn/uc/wap/login/check', data={
            'username': username,
            'password': password
        })
    return sess.post(
        'https://xxcapp.xidian.edu.cn/xisuncov/wap/open-report/save',
        data={
            'sfzx': '1',
            'tw': '1',
            'area': '陕西省 西安市 长安区',
            'city': '西安市',
            'province': '陕西省',
            'address': '陕西省西安市长安区兴隆街道竹园3号宿舍楼西安电子科技大学南校区',
            'geo_api_info': '{"type":"complete","position":{"Q":34.127332356771,"R":108.83943196614598,"lng":108.839432,"lat":34.127332},"location_type":"html5","message":"Get geolocation success.Convert Success.Get address success.","accuracy":30,"isConverted":true,"status":1,"addressComponent":{"citycode":"029","adcode":"610116","businessAreas":[],"neighborhoodType":"","neighborhood":"","building":"","buildingType":"","street":"竹园一路","streetNumber":"248号","country":"中国","province":"陕西省","city":"西安市","district":"长安区","towncode":"610116016000","township":"兴隆街道"},"formattedAddress":"陕西省西安市长安区兴隆街道竹园3号宿舍楼西安电子科技大学南校区","roads":[],"crosses":[],"pois":[],"info":"SUCCESS"}',
            'sfcyglq': '0',
            'sfyzz': '0',
            'qtqk': '',
            'ymtys': '0'}).json()['m']


def get_hour_message() -> str:
    h = datetime.datetime.fromtimestamp(
        int(time.time()), pytz.timezone('Asia/Shanghai')).hour
    if 6 <= h <= 11:
        return '晨'
    elif 12 <= h <= 17:
        return '午'
    elif 18 <= h <= 24:
        return '晚'
    else:
        return '凌晨'


def check(username: str, password: str) -> str:
    message = ''
    try:
        message += commit_data(username, password)
        message += '\n' + (get_hour_message()) + '检-'

    except BaseException:
        message += '信息有误或网页无法打开,操作失败'
    return message

# 体育打卡----------------------------------------------------------------------------------


def cron_check(ses: SportsSession, username: str) -> (bool, str):
    message = ''

    response = ses.post(ses.BASE_URL + 'stuTermPunchRecord/findList',
                        data={
                            'userId': ses.user_id
                        }).json()
    term_id = response['data'][0]['sysTermId']

    response2 = ses.post(ses.BASE_URL + 'stuPunchRecord/findPagerOk',
                         data={
                             'userNum': username,
                             'sysTermId': term_id,
                             'pageSize': 999,
                             'pageIndex': 1
                         }).json()

    vaild_punch_data = response2['data']

    return False, message


def get_sport_record(ses: SportsSession, username: str) -> (bool, str):
    message = ''

    response = ses.post(ses.BASE_URL + 'stuTermPunchRecord/findList',
                        data={
                            'userId': ses.user_id
                        }).json()
    term_id, term_name = response['data'][0]['sysTermId'], response['data'][0]['sysTerm']
    name = response['data'][0]['name']
    vaild_punch_times = response['data'][0]['goodNum']

    message += f"当前学期: {term_name}\n"
    response2 = ses.post(ses.BASE_URL + 'stuPunchRecord/findPagerOk',
                         data={
                             'userNum': username,
                             'sysTermId': term_id,
                             'pageSize': 999,
                             'pageIndex': 1
                         }).json()

    message += f"姓名:{name}\n" \
               f"学号:{username}\n" \
               f"有效打卡次数为:{vaild_punch_times}\n"
    if vaild_punch_times >= 50:
        message += "恭喜您已经完成体育打卡了!,即将为您自动取消订阅"
        return True, message
    vaild_punch_data = response2['data']

    return False, message

# 课表查询------------------------------------------------------------------


def get_timetable(ses: EhallSession, username: str,
                  basic_path: Union[Path, str]):
    semesterCode = ses.post(
        'http://ehall.xidian.edu.cn/jwapp/sys/wdkb/modules/jshkcb/dqxnxq.do',
        headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }
    ).json()['datas']['dqxnxq']['rows'][0]['DM']
    termStartDay = datetime.strptime(ses.post(
        'http://ehall.xidian.edu.cn/jwapp/sys/wdkb/modules/jshkcb/cxjcs.do',
        headers={
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        },
        data={
            'XN': semesterCode.split('-')[0] + '-' + semesterCode.split('-')[1],
            'XQ': semesterCode.split('-')[2]
        }
    ).json()['datas']['cxjcs']['rows'][0]["XQKSRQ"].split(' ')[0], '%Y-%m-%d')
    qResult = ses.post(
        'http://ehall.xidian.edu.cn/jwapp/sys/wdkb/modules/xskcb/xskcb.do',
        headers={  # 学生课程表
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': 'application/json, text/javascript, */*; q=0.01'
        }, data={
            'XNXQDM': semesterCode
        }
    ).json()
    qResult = qResult['datas']['xskcb']  # 学生课程表
    if qResult['extParams']['code'] != 1:
        raise Exception(qResult['extParams']['msg'])

    courseList = []
    for i in qResult['rows']:
        while len(courseList) < len(i['SKZC']):
            courseList.append([[], [], [], [], [], [], []])
        for j in range(len(i['SKZC'])):
            if i['SKZC'][j] == '1' and int(
                    i['KSJC']) <= 10 and int(
                    i['JSJC']) <= 10:
                courseList[j][int(i['SKXQ']) - 1].append({
                    'name': i['KCM'],
                    'location': i['JASMC'],
                    'sectionSpan': (int(i['KSJC']), int(i['JSJC']))
                })
    remake = {}
    for week_cnt in range(len(courseList)):
        for day_cnt in range(len(courseList[week_cnt])):
            if courseList[week_cnt][day_cnt]:
                date = termStartDay + \
                    timedelta(days=week_cnt * 7 + day_cnt)  # 从第一 周的第一天起
                remake[str(
                    parse(f"{date.year}-{date.month}-{date.day}")).split(" ")[0]] = {}
                for course in courseList[week_cnt][day_cnt]:
                    if course['sectionSpan'][0] > 10:
                        continue
                    elif course['location'] is None:
                        course['location'] = '待定'
                    remake[str(parse(f"{date.year}-{date.month}-{date.day}")).split(" ")[0]][int(
                        course['sectionSpan'][1] / 2 - 1)] = {'name': course['name'], 'location': course['location'], }
    # {'2023-01-15':{0:{'name':'', 'location':''}...}}
    with open(os.path.join(basic_path, f"{username}-remake.json"), "w", encoding="utf-8") as f:

        f.write(json.dumps(remake, ensure_ascii=False))


def get_next_course(username: str, basic_path: Union[Path, str]) -> str:
    message = ""
    with open(os.path.join(basic_path, f"{username}-remake.json"), "r", encoding="utf-8") as f:
        courses = json.loads(f.read())
    today = datetime.now()
    if courses.get(
            str(parse(f"{today.year}-{today.month}-{today.day}")).split(" ")[0], None):
        today_course = courses.get(
            str(parse(f"{today.year}-{today.month}-{today.day}")).split(" ")[0], None)
        if today.hour == 8:
            if today_course.get("0", None):
                course = today_course.get("0")
                message += f"小小垚温馨提醒\n今天8:30-10.05\n你有一节 {course['name']} 在 {course['location']}上，\n请合理安排时间，不要迟到"
        elif today.hour == 9:
            if today_course.get("1", None):
                course = today_course.get("1")
                message += f"小小垚温馨提醒\n今天10:25-12:00\n你有一节 {course['name']} 在 {course['location']}上，\n请合理安排时间，不要迟到"
        elif today.hour == 13:
            if today_course.get("2", None):
                course = today_course.get("2")
                message += f"小小垚温馨提醒\n今天14:00-15:35\n你有一节 {course['name']} 在 {course['location']}上，\n请合理安排时间，不要迟到"
        elif today.hour == 15:
            if today_course.get("3", None):
                course = today_course.get("3")
                message += f"小小垚温馨提醒\n今天15:55-17:30\n你有一节 {course['name']} 在 {course['location']}上，\n请合理安排时间，不要迟到"
        elif today.hour == 18:
            if today_course.get("4", None):
                course = today_course.get("4")
                message += f"小小垚温馨提醒\n今天19:00-20:35\n你有一节 {course['name']} 在 {course['location']}上，\n请合理安排时间，不要迟到"
    return message


def get_whole_day_course(username: str, time_sche: List,
                         basic_path: Union[Path, str], _time: int = 0) -> str:
    message = ""
    with open(os.path.join(basic_path, f"{username}-remake.json"), "r", encoding="utf-8") as f:
        courses = json.loads(f.read())
    today = datetime.now()
    y = today.year
    m = today.month
    d = today.day
    if _time == 1:
        d += 1
    if courses.get(str(parse(f"{y}-{m}-{d}")).split(" ")[0], None):

        today_course: Dict = courses.get(
            str(parse(f"{y}-{m}-{d}")).split(" ")[0], None)
        if _time == 0:
            message += f"今天一共有{len(list(today_course.keys()))}节课需要上\n"
        else:
            message += f"明天一共有{len(list(today_course.keys()))}节课需要上\n"
        message += "****************\n"
        for i in range(4):
            if today_course.get(str(i), None):
                message += f"{time_sche[i][0]}-{time_sche[i][1]}\n有一节: {today_course[str(i)]['name']}\n上课地点在: {today_course[str(i)]['location']}\n"
                message += "****************\n"
    else:
        if _time == 0:
            message += "今天没有课哦，安排好时间，合理学习合理放松吧!"
        else:
            message += "明天没有课哦，安排好时间，合理学习合理放松吧!"

    return message


def get_question(mode: int) -> (Message, Message, Message):
    """
    返回一道随机题目以及答案
    :param mode: 1为单选，2为多选，3为任意题型随机
    :return:如果返回None,则为假
    """
    questions_single_des = list(questions_single.keys())
    questions_multi_des = list(questions_multi.keys())
    if mode == 1:
        res = random.choice(questions_single_des)
        ans = questions_single.get(res)
        _type = "[单选题]\n"
    elif mode == 2:
        res = random.choice(questions_multi_des)
        ans = questions_multi.get(res)
        _type = "[多选题]\n"
    elif mode == 3:
        rand = random.random()
        if rand < 0.4:
            res = random.choice(questions_multi_des)
            ans = questions_multi.get(res)
            _type = "[多选题]\n"
        else:
            res = random.choice(questions_single_des)
            ans = questions_single.get(res)
            _type = "[单选题]\n"
    else:
        res = None
        ans = None
        _type = None
    return res, ans, _type


# 空闲教室查询---------------------------------------------------------------------

def get_teaching_buildings(ses: EhallSession) -> List[Tuple]:
    datas = ses.post(
        "https://ehall.xidian.edu.cn/jwapp/sys/kxjas/modules/kxjas/jxlcx.do",
        data={
            "*order": "+XXXQDM,+PX,+JXLDM",
            "querySetting": '[{"name":"XXXQDM","caption":"学校校区","linkOpt":"AND","builderList":"cbl_String","builder":"equal","value":"S","value_display":"南校区"}]',
            "pageSize": "999",
        })
    datas = datas.json()
    jxl = [(x.get("JXLMC"), x.get("JXLDM"))
           for x in datas["datas"]["jxlcx"]["rows"]]

    return jxl


def get_classroom(ses: EhallSession, build: str) -> List:
    querySetting = [{"name": "JXLDM", "caption": "教学楼代码",
                     "builder": "equal", "linkOpt": "AND", "value": build}]
    rooms = ses.post(
        "https://ehall.xidian.edu.cn/jwapp/sys/kxjas/modules/kxjas/cxjsqk.do",
        data={
            "XNXQDM": "2022-2023-2",
            "ZC": "1",
            "XQ": "1",
            "querySetting": str(querySetting),
            "*order": "+LC, +JASMC",
            "pageSize": "999"}).json()
    return [x["JASMC"] for x in rooms["datas"]
            ["cxjsqk"]["rows"] if "休息室" not in x["JASMC"]]


async def httpx_client_post(cookies: RequestsCookieJar, url: str, results: Dict[str, List], data: Dict, s: int, e: int, room: str):
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = (await client.post(url, data=data)).json()
        if not resp["datas"]["xdcxkxjsxq"]["rows"]:
            results[f"{s}-{e}"].append(room)


async def get_idle_classroom(ses: EhallSession, rooms: List,
                             time_: str) -> Dict[str, List[str]]:
    y, m, d = time_.split("-")
    if 1 <= int(m) <= 7:
        XN = f'{int(y)-1}-{y}'
        XQ = '2'
    else:
        XN = f'{y}-{int(y)+1}'
        XQ = '1'
    response = ses.post(
        "https://ehall.xidian.edu.cn/jwapp/sys/kxjas/modules/kxjas/rqzhzcjc.do",
        data={
            "RQ": time_,
            "XN": XN,
            "XQ": XQ,
        }).json()
    XQJ = response["datas"]["rqzhzcjc"]["XQJ"]
    ZC = response["datas"]["rqzhzcjc"]["ZC"]
    time_sche = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
    idle_rooms = {}
    for s, e in time_sche:
        idle_rooms[f'{s}-{e}'] = []
    tasks = []
    cookies = ses.cookies
    for room in rooms:
        for s, e in time_sche:
            # 同步
            # response2 = ses.post(
            #     "https://ehall.xidian.edu.cn/jwapp/sys/kxjas/modules/kxjas/xdcxkxjsxq.do",
            #     data={
            #         "JASDM": room,
            #         "XNXQDM": f"{XN}-{XQ}",
            #         "KSJC": str(s),
            #         "JSJC": str(e),
            #         "ZYLXDM": "01",
            #         "ZC": str(ZC),
            #         "XQ": str(XQJ)}).json()
            # if not response2["datas"]["xdcxkxjsxq"]["rows"]:
            #     idle_rooms[f"{s}-{e}"].append(room)

            # 异步
            tasks.append(
                asyncio.ensure_future(
                    httpx_client_post(
                        cookies=cookies,
                        url="https://ehall.xidian.edu.cn/jwapp/sys/kxjas/modules/kxjas/xdcxkxjsxq.do",
                        results=idle_rooms,
                        data={
                            "JASDM": room,
                            "XNXQDM": f"{XN}-{XQ}",
                            "KSJC": str(s),
                            "JSJC": str(e),
                            "ZYLXDM": "01",
                            "ZC": str(ZC),
                            "XQ": str(XQJ)},
                        s=s,
                        e=e,
                        room=room)))
    await asyncio.wait(tasks)

    # 储存方式为{'1-2':['B-102',...]}
    return idle_rooms


def analyse_best_idle_room(idle_room: Dict[str,
                                           List],
                           timetable: Dict[str,
                                           Dict[int,
                                                Dict[str,
                                                     str]]],
                           time_: str,
                           building: str) -> str:
    message = ''
    time_sche = {
        0: "1-2",
        1: "3-4",
        2: "5-6",
        3: "7-8",
        4: "9-10",
        5: "晚自习"
    }
    # 如果这一天有课
    if timetable.get(time_, None):
        today_course = timetable.get(time_, None)
        course_locations = [x["location"] for x in today_course.values()]
        course_buildings = [x.split("-")[0] for x in course_locations]
        course_rooms = [x.split("-")[1] for x in course_locations]
        same_building = {}
        flag = 0
        for i in range(len(course_buildings)):
            result = []
            # 有同一栋楼
            if course_buildings[i] == building:
                flag = 1
                course_time = int(list(today_course.keys())[i])
                course_floor = course_rooms[i][0]
                if course_time != 4:
                    for room in idle_room[time_sche[course_time + 1]]:
                        if room.split("-")[1][0] == course_floor:
                            result.append(room.split("-")[1])
                for room in idle_room[time_sche[course_time - 1]]:
                    if room.split("-")[1][0] == course_floor:
                        result.append(room.split("-")[1])
                collection_rooms = Counter(result)
                best_ans = collection_rooms.most_common(1)
                message += f"结合您{time_}的课表推荐您第{time_sche[course_time]}节课（{list(today_course.values())[i]['name']}）前后去{building}-{best_ans[0][0]}教室自习，离您的教室较近且空的时间较多,足足有{best_ans[0][1]}节课\n"
        if flag == 0:
            message += f"结合您{time_}的课表，您在当天有课，但不在{building},即将为您推荐{building}空闲时间最多的教室。但可能更换自习地点会有更好的选择哦\n"
    else:
        message += f"鉴于您{time_}的课表没有课，已为您推荐当天{building}空闲时间最多的教室\n"
    ans = []
    for k, v in idle_room.items():
        ans += v
    collection_rooms = Counter(ans)
    best_ans2 = collection_rooms.most_common(5)
    message += "空闲时间排名前五的教室分别为:\n"
    for c, t in best_ans2:
        message += f"{c}教室，空闲{t}节课\n"
    message += "祝您学习生活愉快!"
    return message


def get_min_distance_aed(now_lat: str = "34.12501587001219",
                         now_lng: str = "108.8326315482191") -> (Dict, float, List):
    response = requests.get(
        "https://gis.xidian.edu.cn/openmap/mapi/place/v1/list?",
        params={
            "category": "AED",
            "location": f"{now_lng},{now_lat}"
        }).json()
    aed_infos = []
    min_dist = np.inf
    aed_min_dist = {}
    for aed in response["result"]:
        if aed["campus"] == "南校区":
            info = {
                "id": aed["id"],
                "campus": "南校区",
                "loc": aed["name"].replace(
                    "(南校区）",
                    "").replace(
                    "AED",
                    ""),
                "description": aed["description"].replace(
                    "\n",
                    '').replace(
                    "位置：",
                    ""),
                "distance": aed["distance"],
                "lat": aed["location"]["y"],
                "lng": aed["location"]["x"]}
        else:
            info = {
                "id": aed["id"],
                "campus": "北校区",
                "loc": aed["name"].replace(
                    "(北校区）",
                    "").replace(
                    "AED",
                    ""),
                "description": aed["description"].replace(
                    "\n",
                    '').replace(
                    "位置：",
                    ""),
                "distance": aed["distance"],
                "lat": aed["location"]["x"],
                "lng": aed["location"]["y"]}
        if min_dist > info["distance"]:
            min_dist = info["distance"]
            aed_min_dist = info
        if info["id"] == 282418 or info["id"] == 282419 or info["id"] == 282414 or info[
                "id"] == 282417 or info["id"] == 282343 or info["id"] == 282365 or info["id"] == 282351:
            aed_infos.append(info)
    return aed_min_dist, min_dist, aed_infos


def get_signed_url(url: str) -> str:
    m = hashlib.md5()
    m.update(url.encode(encoding="utf-8"))
    return '&sig=' + m.hexdigest()


def get_url_routeplan(
        now_lat: str,
        now_lng: str,
        tar_lat: str,
        tar_lng: str,
        SK: str,
        appname: str) -> str:
    base_url = "https://apis.map.qq.com"
    ori_url = f"/uri/v1/routeplan?type=drive&fromcoord={now_lat},{now_lng}&to=AED&tocoord={tar_lat},{tar_lng}&policy=0&referer={appname}"
    signed_url = ori_url + get_signed_url(ori_url + SK)
    url = base_url + signed_url
    return url


def get_url_marker(lat: str, lng: str, SK: str, appname: str) -> str:
    base_url = "https://apis.map.qq.com"
    ori_url = f"/uri/v1/marker?marker=coord:{lat},{lng};title:AED;addr:AEDAddress&referer={appname}"
    signed_url = ori_url + get_signed_url(ori_url + SK)
    url = base_url + signed_url
    return url

# 每日健康信息---------------------------------------------------------------------


def punch_daily_health(username:str, password:str)->str:

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4515.159 Safari/537.36'
    }
    data = {
        "username": username,
        "password": password,
    }
    url = 'https://xxcapp.xidian.edu.cn/uc/wap/login/check'

    session = requests.session()
    session.post(url, headers=headers, data=data)
    cookies = session.cookies.items()
    cookie = ''
    for name, value in cookies:
        cookie += '{0}={1};'.format(name, value)

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Length": "87",
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie,
        "DNT": "1",
        "Host": "xxcapp.xidian.edu.cn",
        "Origin": "https://xxcapp.xidian.edu.cn",
        "Pragma": "no-cache",
        "Referer": "https://xxcapp.xidian.edu.cn/site/newForm/index?formid=810",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.70",
        "X-Requested-With": "XMLHttpRequest",
        "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Microsoft Edge\";v=\"109\", \"Chromium\";v=\"109\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
    }


    data = {
        "formid": "810",
    }
    response = requests.post('https://xxcapp.xidian.edu.cn/forms/wap/default/get-info?formid=810', headers=headers,
                             data=data)
    res_js = json.loads(response.text)
    value = res_js["d"]["value"]
    data = {
        "value[date_810_2]": datetime.now().strftime("%Y-%m-%d"),
        "value[id]": value["id"],
        "value[radio_810_1]": value["radio_810_1"],
        "formid": "810",
    }

    response2 = requests.post('https://xxcapp.xidian.edu.cn/forms/wap/default/save', headers=headers, data=data)
    res_js = json.loads(response2.text)

    token = ""  # pushplus的token
    title = "返校|" + res_js["m"]
    content = title

    requests.get(f'http://www.pushplus.plus/send?token={token}&title={title}&content={content}&template=html')
    return res_js["m"]


# 加密解密-------------------------------------------------------------------------


def des_encrypt(s: str, key: str) -> bytes:
    secret_key = key
    iv = secret_key
    des_obj = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
    secret_bytes = des_obj.encrypt(s, padmode=PAD_PKCS5)
    return binascii.b2a_hex(secret_bytes)


def des_descrypt(s: str, key: str) -> bytes:
    secret_key = key
    iv = secret_key
    des_obj = des(secret_key, CBC, iv, pad=None, padmode=PAD_PKCS5)
    decrypt_str = des_obj.decrypt(binascii.a2b_hex(s), padmode=PAD_PKCS5)
    return decrypt_str

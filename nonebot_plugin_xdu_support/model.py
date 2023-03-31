import pytz
from libxduauth import EhallSession, SportsSession
import json
from datetime import datetime, timedelta
from typing import List, Dict, Union, Tuple
from pathlib import Path
import os
from .data_source import questions_multi, questions_single
import random
from pyDes import des, CBC, PAD_PKCS5
import binascii
from requests.cookies import RequestsCookieJar
import httpx
from collections import Counter
from dateutil.parser import parse
import numpy as np
import hashlib
from requests import Session
import requests
from Crypto.PublicKey import RSA
import base64
from Crypto.Cipher import PKCS1_v1_5
import time
import re
import jieba.posseg as psg
import jieba
from jieba import lcut
import jionlp as jio
import asyncio
from nonebot.adapters.onebot.v11 import MessageEvent, Message

# 添加新词
words = [
    "体育打卡",
    '考试',
    "xdu功能订阅",
    "xdu功能退订",
    "青年大学习",
    '空闲教室',
    "成绩",
    "信远",
    "更新",
    "课表"
]
search_wd = ["课表", "体育打卡", "成绩", "考试"]


Model = {
    "体育打卡": "体育打卡",
    "课表": "课表提醒",
    "马原": "马原测试",
    "空闲教室": "空闲教室查询",
    "青年大学习": "青年大学习",
    "成绩": "成绩查询",
    "提醒": "提醒",
    "考试": "考试查询"
}

exist_md = ["体育打卡", "课表", "马原", "空闲教室", "青年大学习", "成绩", "提醒", "考试"]


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
    h = datetime.fromtimestamp(
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


async def httpx_client_post(cookies: RequestsCookieJar, url: str, results: Dict[str, List], data: Dict, s: int, e: int, room: str, stop_classroom: List):
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = (await client.post(url, data=data)).json()
        if not resp["datas"]["xdcxkxjsxq"]["rows"] and room not in stop_classroom:
            results[f"{s}-{e}"].append(room)


async def get_idle_classroom(ses: EhallSession, rooms: List,
                             time_: str, stop_classroom: List) -> Dict[str, List[str]]:
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
                        room=room,
                        stop_classroom=stop_classroom)))
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
        course_buildings = [
            x.split("-")[0] if x != "待定" or x != "在线导学" else x for x in course_locations]
        course_rooms = [
            x.split("-")[1] if x != "待定" or x != "在线导学" else x for x in course_locations]

        flag = 0
        message = f"结合您{time_}的课表\n****************\n"
        for i in range(len(course_buildings)):
            if course_buildings[i] == "待定" or course_buildings[i] == "在线导学":
                continue
            result = []
            # 有同一栋楼
            if course_buildings[i] == building:
                flag = 1
                course_time = int(list(today_course.keys())[i])
                course_floor = course_rooms[i][0]
                if course_time != 4:
                    result += [room.split("-")[1] for room in idle_room[time_sche[course_time + 1]]
                               if room.split("-")[1][0] == course_floor]
                if course_time != 0:
                    result += [room.split("-")[1] for room in idle_room[time_sche[course_time - 1]]
                               if room.split("-")[1][0] == course_floor]
                result = [abs(int(x) - int(course_rooms[i])) for x in result]
                collection_rooms = dict(Counter(result))
                collection_rooms = sorted(
                    collection_rooms.items(), key=lambda x: (-x[1], x[0]))
                best_ans = collection_rooms[0]
                message += f"推荐您在第{time_sche[course_time]}节课（{list(today_course.values())[i]['name']}）前后\n去 {building}-{best_ans[0]+int(course_rooms[i])} 教室自习\n" \
                           f"离您的本节课教室（{course_buildings[i]}-{course_rooms[i]}）较近且空的时间较多,足足有{best_ans[1]}节课\n" \
                           f"****************\n"
        if flag == 0:
            message += f"您在当天有课，但不在{building},即将为您推荐{building}空闲时间最多的教室。但可能更换自习地点会有更好的选择哦\n" \
                       f"****************\n"
    else:
        message += f"鉴于您{time_}的课表,您当天并没有课，已为您推荐当天{building}空闲时间最多的教室\n" \
                   f"****************\n"
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


# AED查询---------------------------------------------------------------------------------

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


def punch_daily_health(username: str, password: str) -> str:

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
    response = requests.post(
        'https://xxcapp.xidian.edu.cn/forms/wap/default/get-info?formid=810',
        headers=headers,
        data=data)
    res_js = json.loads(response.text)
    value = res_js["d"]["value"]
    data = {
        "value[date_810_2]": datetime.now().strftime("%Y-%m-%d"),
        "value[id]": value["id"],
        "value[radio_810_1]": value["radio_810_1"],
        "formid": "810",
    }

    response2 = requests.post(
        'https://xxcapp.xidian.edu.cn/forms/wap/default/save',
        headers=headers,
        data=data)
    res_js = json.loads(response2.text)

    token = ""  # pushplus的token
    title = "返校|" + res_js["m"]
    content = title

    requests.get(
        f'http://www.pushplus.plus/send?token={token}&title={title}&content={content}&template=html')
    return res_js["m"]


# 青年大学习未完成名单获取--------------------------------------------------------------------------

def get_verify(ses: Session, base_path: Union[Path, str]):
    content = ses.get(
        "https://api.sxgqt.org.cn/bgsxapiv2/login/verify").content
    with open(os.path.join(base_path, "verify.png"), "wb") as f:
        f.write(content)


def get_youthstudy_names(ses: Session,
                         verify: str,
                         username: str,
                         password: str) -> (bool,
                                            str):
    msg = ""
    public_key = "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyDwpaSAik1ORaCphEU7j\nZsWuvEIy4Zwu2LkyH+cI71oIwPN9z0uTpWrswB+DHVGp/WprDok9B2tEyYYnRKgT\nSsYhJLIgAcehyrPm0R72E+wFZvxS4VHIyLIRznhuq5Dge7MrVcbTPGT9bppKYZM8\ncujagOPfG7OtxBnNJAWTfGXKrKFltjGh+02YZ2co9DT+rjN1hzcSd8nRZOuEX89j\ny3eRKxz+fQEpwdkV3ZYFLj3QhlRrxzNAoIcseV0FKhW9d5NruVEGQAIswjqbFpgF\n7ykEddCqpa2nBnb7Aao+BGE6Q5K/enBnILrZDpoSwNEvzt54d6gYZoHZA6+A9Dta\nOwIDAQAB\n-----END PUBLIC KEY-----"
    res = ses.post(
        "https://api.sxgqt.org.cn/bgsxapiv2/admin/login",
        data={
            "account": username,
            "is_quick": 0,
            "pass": f"{encryption(password,public_key.encode('utf-8'))}",
            "verify": verify})
    resp = res.json()
    if resp.get("msg") != "success":
        return False, "验证码错误"
    user_name = resp.get("data").get("username")
    msg += f"成功登录陕西青年大学习\n当前用户为{user_name}\n"
    token = resp.get("data").get("token")
    headers = {
        "token": token
    }
    origin = ses.get(
        "https://api.sxgqt.org.cn/bgsxapiv2/organization/getOrganizeMess",
        headers=headers).json()
    oid = origin.get("data").get("pid")
    id = origin.get("data").get("id")
    msg += f"当前组织id为{id}\n本组织内当期青年大学习未完成的有：\n"
    students = ses.get(
        f"https://api.sxgqt.org.cn/bgsxapiv2/regiment?page=1&rows=100&keyword=&oid={id}&leagueStatus=&goHomeStatus=&memberCardStatus=&isPartyMember=&isAll=",
        headers=headers).json().get("data").get("data")
    for student in students:
        if student.get("isStudy") == "否":
            msg += f'{student.get("realname")}  '
    return True, msg


# 成绩查询-------------------------------------------------------------------------

def get_terms(ses: EhallSession) -> List:
    # res[0]['XNXQDM']
    res = ses.post(
        # 查询当前学年学期和上一个学年学期
        'http://ehall.xidian.edu.cn/jwapp/sys/cjcx/modules/cjcx/cxdqxnxqhsygxnxq.do',
    ).json()['datas']['cxdqxnxqhsygxnxq']['rows']
    return res


def get_grade(ses: EhallSession) -> (List, str):

    msg = []

    terms = [term["XNXQDM"] for term in get_terms(ses)]
    querySetting = [
        {
            "name": "SFYX",
            "caption": "是否有效",
            "linkOpt": "AND",
            "builderList": "cbl_m_List",
            "builder": "m_value_equal",
            "value": "1",
            "value_display": "是"
        },
        {
            "name": "SHOWMAXCJ",
            "caption": "显示最高成绩",
            "linkOpt": "AND",
            "builderList": "cbl_m_List",
            "builder": "m_value_equal",
            "value": "0",
            "value_display": "否"
        }
    ]

    total = [0, 0]
    course_ignore = [
        '军事',
        '形势与政策',
        '创业基础',
        '新生',
        '写作与沟通',
        '学科导论',
        '心理',
        '物理实验']
    types_ignore = ['公共任选课', '集中实践环节', '拓展提高', '通识教育核心课', '专业选修课']
    unpassed_course = {}

    for i in ses.post(
            'http://ehall.xidian.edu.cn/jwapp/sys/cjcx/modules/cjcx/xscjcx.do',
            data={
                'querySetting': json.dumps(querySetting),
                '*order': '+XNXQDM,KCH,KXH',
                'pageSize': 1000,
                'pageNumber': 1
            }
    ).json()['datas']['xscjcx']['rows']:
        flag = 0

        for lx in types_ignore:
            if i["KCLBDM_DISPLAY"].find(lx) != -1:
                flag = 1
                break

        for kw in course_ignore:
            if i["XSKCM"].find(kw) != -1:
                flag = 1
                break

        if flag == 1:
            i["XSKCM"] = '*' + i["XSKCM"]
        else:
            if i["SFJG"] == '1':  # 及格
                if i["CXCKDM"] == '01':  # 初修
                    total[0] += i["XF"] * i["ZCJ"]
                    total[1] += i["XF"]
                else:
                    total[0] += i["XF"] * 60.0
                    total[1] += i["XF"]

        if i["SFJG"] == '0' and i["KCXZDM_DISPLAY"] == "必修":
            unpassed_course[i["KCH"]] = i["XF"]
        elif i["SFJG"] == '1' and i["KCH"] in unpassed_course.keys():
            del unpassed_course[i["KCH"]]

        roman_nums = str.maketrans({'Ⅰ': 'I',
                                    'Ⅱ': 'II',
                                    'Ⅲ': 'III',
                                    'Ⅳ': 'IV',
                                    'Ⅴ': 'V',
                                    'Ⅵ': 'VI',
                                    'Ⅶ': 'VII',
                                    'Ⅷ': 'VIII',
                                    })  # 一些终端无法正确打印罗马数字
        i["XSKCM"] = i["XSKCM"].translate(roman_nums)
        if i["XNXQDM"] in terms:
            res = f'{i["XNXQDM"]}\n' \
                  f'[{i["KCH"]}]{i["XSKCM"]}\n' \
                  f'{i["KCXZDM_DISPLAY"]}\n' \
                  f'{i["ZCJ"] if i["ZCJ"] else "还没出成绩"}\n' \
                  f'{i["KCLBDM_DISPLAY"]}'
            msg.append(res)
    msg.append(f'未获得的学分有：{sum(unpassed_course.values())}')
    msg.append('注：标记有*的课程以及未通过科目不计入均分')

    return msg, f'入学来的加权平均成绩：{total[0] / total[1]:.2f}'

# 考试时间获取--------------------------------------------------------------------


def get_examtime(flag: int, ses: EhallSession) -> (str, List):
    terms_url = "https://ehall.xidian.edu.cn/jwapp/sys/studentWdksapApp/modules/wdksap/xnxqcx.do"
    term = ses.post(terms_url,
                    data={
                        "*order": "-PX,-DM"
                    }).json()["datas"]["xnxqcx"]["rows"][flag]["DM"]

    examtime_url = "https://ehall.xidian.edu.cn/jwapp/sys/studentWdksapApp/modules/wdksap/wdksap.do"
    data = {
        "XNXQDM": term,
        "*order": "-KSRQ,-KSSJMS"
    }
    examtime = ses.post(examtime_url, data=data).json()[
        "datas"]["wdksap"]["rows"]

    return term, examtime

# 命令预处理


def get_eventname(text: Message) -> str:
    key = psg.lcut(text)
    kw = jio.keyphrase.extract_keyphrase(text)
    flag = 0
    first_v = "去"
    for w, p in key:
        if p == "v":
            if flag == 0:
                flag = 1
            else:
                first_v = w
                break
    pattern1 = f"{first_v}(.*?{kw[-1]})"
    if len(kw) == 1:
        pattern2 = f"{kw[0]}"
    elif len(kw) > 1:
        pattern2 = f"{kw[0]}.*?{kw[-1]}"
    else:
        return ""
    event_name1 = re.findall(pattern1, text)[0]
    event_name2 = re.findall(pattern2, text)[0]
    event_name = event_name1 if len(event_name1) > len(
        event_name2) else event_name2
    return event_name


def generate_event(event: MessageEvent, cmd: str) -> MessageEvent:
    msg_event = MessageEvent(time=int(time.time()),
                             self_id=event.self_id,
                             post_type="message",
                             sub_type="friend",
                             user_id=event.user_id,
                             message_type="private",
                             message_id=event.message_id,
                             message=[{"type": "text",
                                       "data": {"text": f"{cmd}"}}],
                             original_message=[{"type": "text",
                                                "data": {"text": f"{cmd}"}}],
                             raw_message=f"{cmd}",
                             font=0,
                             sender={"user_id": event.sender.user_id,
                                     "nickname": event.sender.nickname,
                                     "sex": event.sender.sex,
                                     "age": event.sender.age,
                                     "card": event.sender.card,
                                     "area": event.sender.area,
                                     "level": event.sender.level,
                                     "role": event.sender.role,
                                     "title": event.sender.title},
                             to_me=event.to_me,
                             reply=event.reply,
                             target_id=1850602750)
    return msg_event


def get_handle_event(
        tx: Message, event: MessageEvent) -> Union[MessageEvent, str]:
    for wd in words:
        jieba.add_word(wd)
    word_list = lcut(tx)

    if "订阅" in word_list:
        for ex_md in exist_md:
            if ex_md in word_list:
                msg_event = generate_event(event, f"xdu功能订阅 {Model[ex_md]}")
                return msg_event
    elif "退订" in word_list:
        for ex_md in exist_md:
            if ex_md in word_list:
                msg_event = generate_event(event, f"xdu功能退订 {Model[ex_md]}")
                return msg_event
    else:
        for search in search_wd:
            if search in word_list:
                if search == "课表" and "更新" in word_list:
                    msg_event = generate_event(event, f"更新课表")
                else:
                    msg_event = generate_event(event, f"{search}查询")
                return msg_event
        if "空闲教室" in word_list:
            build = ""
            for wd in word_list:
                if wd in ["A", "B", "C", "D", "信远", "E"]:
                    build += wd + "教学楼"
                elif wd in ["I", "II", "III"]:
                    build += wd + "区"
            try:
                time_select = jio.parse_time(
                    tx, time_base=time.time()).get("time")[0].split(" ")[0]
            except BaseException:
                time_select = ""
            msg_event = generate_event(event, f"空闲教室查询 {build} {time_select}")
            return msg_event
        elif "提醒" in word_list:
            event_name = get_eventname(tx)
            if not event_name:
                msg_event = generate_event(event, f"提醒")
            else:
                try:
                    time_select = jio.parse_time(
                        tx, time_base=time.time()).get("time")[0].split(" ")[0]
                except BaseException:
                    time_select = ""
                msg_event = generate_event(
                    event, f"提醒 {event_name} {time_select}")
            return msg_event
        elif "青年大学习" in word_list:
            msg_event = generate_event(event, "青年大学习")
            return msg_event
        else:
            return ""


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


def encryption(text: str, public_key: bytes):
    # 字符串指定编码（转为bytes）
    text = text.encode('utf-8')
    # 构建公钥对象
    cipher_public = PKCS1_v1_5.new(RSA.importKey(public_key))
    # 加密（bytes）
    text_encrypted = cipher_public.encrypt(text)
    # base64编码，并转为字符串
    text_encrypted_base64 = base64.b64encode(text_encrypted).decode()
    return text_encrypted_base64

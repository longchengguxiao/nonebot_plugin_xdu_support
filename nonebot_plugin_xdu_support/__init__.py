import time
import re
import asyncio
import os
import json
import requests
from builtins import ConnectionError
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Union

from nonebot_plugin_apscheduler import scheduler
from nonebot.plugin import on_command, on_notice, on_message
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, GroupMessageEvent, Message, MessageEvent, MessageSegment, Bot, PokeNotifyEvent, PRIVATE_FRIEND
from nonebot.typing import T_State
from nonebot.params import ArgStr, CommandArg, Arg, EventPlainText
from nonebot.message import handle_event
from nonebot import require
import nonebot

import jionlp as jio
from libxduauth import EhallSession, SportsSession, XKSession
from .model import check, cron_check, get_sport_record, get_timetable, get_whole_day_course, get_next_course, get_question, get_teaching_buildings, get_classroom, get_idle_classroom, get_url_marker, get_url_routeplan, get_min_distance_aed, des_encrypt, des_descrypt, analyse_best_idle_room, punch_daily_health, get_youthstudy_names, get_verify, get_grade, get_examtime, get_handle_event, get_eventname
from .config import Config


# 启动定时器---------------------------------------------------------------

require("nonebot_plugin_apscheduler")


# 配置初始项---------------------------------------------------------------

MODLE = {
    # "晨午晚检": "Ehall",
    # "学生健康信息":"Ehall",
    "体育打卡": "Sports",
    "课表提醒": "Ehall",
    "选课操作": "XK",
    "马原测试": "MY",
    "空闲教室查询": "Ehall",
    "青年大学习": "Youth",
    "成绩查询": "Ehall",
    "提醒": "TX",
    "考试查询": "Ehall"
}

MODEL_NEED = {
    "Ehall": ["学号", "一站式大厅密码"],
    "Sports": ["学号", "体适能密码"],
    "XK": ["学号", "选课密码"],
    "MY": ["随便输入一些吧，反正也不需要补充信息~"],
    "Youth": ["陕西青少年大数据服务平台账号", "青少年大数据密码"],
    "TX": ["随便输入一些吧，反正也不需要补充信息~"]
}

MODEL_RUN_TIME = {
    # "晨午晚检": "被动：每天7/13/20点自动打卡，定位在南校区\n主动（晨午晚检查看/查看晨午晚检）：返回本阶段是否已打卡",
    # "学生健康信息": "被动：每天早上8点打卡，并且返回信息\n主动（学生健康信息查看）：返回本阶段是否打卡",
    "体育打卡": "被动：每10分钟检测一次，如果您有已上报的正在打卡的记录将会提醒您\n主动（体育打卡查看/查看体育打卡）：返回当前打卡次数信息",
    "课表提醒": "被动：每天早上7点私聊提醒一次今天课表上的课及其位置，每节课前30分钟提醒下节有课\n主动（空闲教室）：返回当天课表以及此时有没有课，最近的课是在什么时候",
    "选课操作": "暂未编写，但在计划内",
    "马原测试": "被动：无\n主动：返回一道单选或者多选题,可以通过参数决定，无参数默认随机",
    "空闲教室查询": "主动:返回查找日期的空闲教室，会经过优化",
    "青年大学习": "主动返回本组织内当期青年大学习未完成名单",
    "成绩查询": "返回所有必修课均分以及近两学期课程的详细分数",
    "提醒": "记下哪些ddl吧，通过戳一戳返回",
    "考试查询": "返回最近学期的考试时间"
}

TIME_SCHED = [
    ("8:30", "10:05"),
    ("10:25", "12:00"),
    ("14:00", "15:35"),
    ("15:55", "17:30"),
    ("19:00", "20:35")
]

global_config = nonebot.get_driver().config
xdu_config = Config.parse_obj(global_config.dict())
xdu_support_path = xdu_config.xdu_support_path
superusers = xdu_config.superusers
DES_KEY = xdu_config.des_key
SK = xdu_config.sk
appname = xdu_config.appname

if not DES_KEY:
    DES_KEY = "mdbylcgx"
else:
    if len(DES_KEY) != 8:
        raise KeyError("DES_KEY必须是八位的字符串，请重新设置")

if xdu_support_path == Path():
    xdu_support_path = os.path.expanduser(
        os.path.join('~', '.nonebot_plugin_xdu_support')
    )

XDU_SUPPORT_PATH = os.path.join(xdu_support_path, "user_data")

if not os.path.exists(XDU_SUPPORT_PATH):
    os.makedirs(XDU_SUPPORT_PATH)

if not os.path.exists(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query")):
    os.makedirs(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query"))

for name in MODLE.values():
    if not os.path.exists(os.path.join(XDU_SUPPORT_PATH, f"{name}.txt")):
        f = open(os.path.join(XDU_SUPPORT_PATH, f"{name}.txt"), 'w')
        f.close()

STATE_OK = True
STATE_ERROR = False


# 注册匹配器----------------------------------------------------------------

add_sub = on_command(
    "xdu功能订阅",
    aliases={
        "xdu服务订阅",
        "xdu添加订阅"},
    priority=4,
    block=True)
cancel_sub = on_command(
    "xdu取消订阅",
    aliases={
        "xdu功能退订",
        "xdu服务退订"},
    priority=4,
    block=True)
#
# chenwuwanjian = on_command(
#     "晨午晚检查看",
#     priority=6,
#     block=True,
#     aliases={"查看晨午晚检"})
#
# daily_health_info = on_command(
#     "学生健康信息查看",
#     priority=6,
#     block=True,
#     aliases={"查看学生健康信息"})

sport_punch = on_command(
    "体育打卡查看",
    priority=6,
    block=True,
    aliases={
        "查看体育打卡",
        "体育打卡查询",
        "查询体育打卡",
        "我的体育打卡"})
timetable = on_command(
    "课表查询",
    priority=5,
    block=True,
    aliases={
        "课表查看",
        "查看课表",
        "查询课表",
        "我的课表"})
update_timetable = on_command("更新课表", priority=5, block=True, aliases={"课表更新"})
mayuan = on_command("马原", priority=6, block=True)
idle_classroom_query = on_command(
    "空闲教室查询", priority=6, block=True, aliases={
        "空闲教室查看", "查询空闲教室", "查看空闲教室"})
stop_classroom = on_command(
    "添加停止教室",
    priority=5,
    block=True,
    aliases={"停止教室添加"})

aed_search = on_command("aed", priority=6, block=True, aliases={"AED"})

youthstudy = on_command("青年大学习", priority=5, block=True, aliases={"未完成学习"})

grade = on_command("成绩查询", priority=5, block=True, aliases={"我的成绩", "查询成绩"})

examination = on_command(
    "考试查询",
    priority=5,
    block=True,
    aliases={
        "我的考试",
        "查询考试"})

remind = on_command("提醒", priority=5, block=True, aliases={"记事", "添加"})

remind_finish = on_command("完成", priority=5, block=True, aliases={"结束", "移除"})

remind_poke = on_notice(priority=5, block=True)

cmd = on_message(block=True, permission=PRIVATE_FRIEND, priority=9)

# 功能订阅-----------------------------------------------------------------


@add_sub.handle()
async def handle(state: T_State, args: Message = CommandArg()):
    msg = args.extract_plain_text().strip()
    if msg and msg in MODLE.keys():
        state["model"] = msg
    else:
        await asyncio.sleep(1)
        res = "现运行的功能有:\n"
        res += "==========================\n"
        for model in MODLE.keys():
            res += model + "\n"
        res += "==========================\n"
        # for model, model_run_time in MODEL_RUN_TIME.items():
        #     res += f"{model}功能的用法为{model_run_time}\n\n"
        res += f"更多信息请查看https://lcgx.xdu.org.cn/#/nonebot_plugin_xdu_support/README?id=%e5%bf%ab%e9%80%9f%e5%bc%80%e5%a7%8b"
        await add_sub.send(res)
        await asyncio.sleep(0.5)


@add_sub.got("model", prompt="请输入想要订阅的功能名称")
async def got_model(event: PrivateMessageEvent, state: T_State, model_: str = ArgStr("model")):
    if model_ in ["取消", "算了"]:
        await add_sub.finish("已取消本次操作")
    model = MODLE.get(model_, None)
    state["model"] = model_
    await asyncio.sleep(1)
    if model:
        user_id = str(event.user_id)
        path = Path(XDU_SUPPORT_PATH, f"{model}.txt")
        state["path"] = path
        flag, users = read_data(path)
        if flag:
            users_id = [x[0] for x in users]
            state["user_id"] = user_id
            state["users"] = users
            if user_id in users_id:
                await add_sub.finish(f"您已经订阅{model_}功能哟~")
            else:
                infos = MODEL_NEED[model]
                state["infos"] = infos
                res = "你需要补充的信息有：\n"
                res += "==========================\n"
                for info in infos:
                    res += info + '\n'
                res += "虽然对密码进行了加密处理，但是很遗憾，所有加密都是可逆的，如果不了解bot的主人请谨慎使用插件，谨慎填写密码。可以回复'算了'或者'取消'来取消本次操作，或者在使用完功能后及时取消订阅以免造成损失"
                await add_sub.send(res)
        else:
            await add_sub.finish("读取信息出错了，请及时联系管理员")
    else:
        await add_sub.finish("输入有误，请重新检查您想订阅的功能名称并重试")


@add_sub.got("info", prompt="请以空格对不同信息进行分割，并且不要改变顺序,例如'123456789 abcdefghi'")
async def got_info(event: PrivateMessageEvent, state: T_State, info: str = ArgStr("info")):
    if info in ["取消", "算了"]:
        await add_sub.finish("已取消本次操作")
    flag = 0
    await asyncio.sleep(1)
    path = state["path"]
    info = info.replace(
        "&amp;",
        "&").replace(
        "&#44;",
        ",").replace(
            "&#91;",
            "[").replace(
                "&#93;",
        "]").split()
    users = state["users"]
    user_id = state["user_id"]
    infos = state["infos"]
    if "一站式大厅密码" in infos:
        try:
            ses = EhallSession(info[0], info[1])
            ses.close()
        except ConnectionError:
            flag = 1
    elif "体适能密码" in infos:
        try:
            ses = SportsSession(info[0], info[1])
            ses.close()
        except ConnectionError:
            flag = 1
    elif "选课密码" in infos:
        try:
            ses = XKSession(info[0], info[1])
            ses.close()
        except ConnectionError:
            flag = 1
    if flag == 0:
        if infos[0] == "随便输入一些吧，反正也不需要补充信息~":
            users.append([user_id, "0", "0"])
        else:
            users.append([user_id] +
                         [info[0], des_encrypt(info[1], DES_KEY).decode()])
        if write_data(path=path, data=users):
            await add_sub.finish(f"成功订阅功能{state['model']}")
        else:
            await add_sub.finish(f"{state['model']}功能订阅失败,请联系管理员")
    else:
        await add_sub.finish("您输入的信息有误请核对后再输入，如果确实无误请联系管理员")


@add_sub.handle()
async def group_handle(event: GroupMessageEvent):
    await asyncio.sleep(1)
    await add_sub.finish("请在聊中处理，本功能不支持群聊")

# 取消订阅---------------------------------------------------------------------------


@cancel_sub.handle()
async def handle(state: T_State, args: Message = CommandArg()):
    msg = args.extract_plain_text().strip()
    if msg and msg in MODLE.keys():
        state["model"] = msg
    else:
        await asyncio.sleep(1)
        res = "现运行的功能有:\n"
        for model in MODLE.keys():
            res += model + "\n"
        await cancel_sub.send(res)


@cancel_sub.got("model", prompt="请输入想要取消订阅的功能名称")
async def got_model(event: MessageEvent, model_: str = ArgStr("model")):
    if model_ in ["取消", "算了"]:
        await cancel_sub.finish("已取消本次操作")

    model = MODLE.get(model_, None)
    await asyncio.sleep(1)
    if model:
        user_id = str(event.user_id)
        path = Path(XDU_SUPPORT_PATH, f"{model}.txt")
        flag, users = read_data(path)
        if flag:
            users_id = [x[0] for x in users]
            if user_id in users_id:
                users.pop(users_id.index(user_id))
                if write_data(path, users):
                    await cancel_sub.finish(f"已经取消{model_}功能的订阅啦！")
                else:
                    await cancel_sub.finish(f"取消{model_}订阅失败，请联系管理员")
            else:
                await cancel_sub.finish(f"您尚未订阅{model_}功能哟~")
        else:
            await cancel_sub.finish("读取信息出错，请及时联系管理员")
    else:
        await cancel_sub.finish("输入有误，请重新检查您想订阅的功能名称并重试")

# 晨午晚检---------------------------------------------------------------------------
# 暂停使用

#
# @chenwuwanjian.handle()
# async def _(event: MessageEvent):
#     path = Path(XDU_SUPPORT_PATH, 'Ehall.txt')
#     flag, users = read_data(path)
#     users_id = [x[0] for x in users]
#     user_id = str(event.user_id)
#     if flag:
#         if user_id in users_id:
#             username = users[users_id.index(user_id)][1]
#             password = des_descrypt(
#                 users[users_id.index(user_id)][2], DES_KEY).decode()
#             message = check(username, password)
#             await chenwuwanjian.finish(message=f'[{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}] {message}')
#         else:
#             await chenwuwanjian.finish("您没有订阅晨午晚检功能，请先订阅再进行查看",)
#     else:
#         await chenwuwanjian.finish("获取数据失败，请联系管理员")
#
#
# # 定时7,14,20
# @scheduler.scheduled_job("cron", hour="7,14,20", month="2-7,9-12")
# async def run_every_7_hour():
#     bot = nonebot.get_bot()
#     path = Path(XDU_SUPPORT_PATH, 'Ehall.txt')
#     flag, users = read_data(path)
#     if flag:
#         for user in users:
#             message = check(user[1], des_descrypt(user[2], DES_KEY).decode())
#             await bot.send_private_msg(user_id=int(user[0]),
#                                        message=f'[{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}] {message}')
#     else:
#         await bot.send_private_msg(user_id=int(superusers[0]),
#                                    message='晨午晚检读取数据失败，快维修')


# 每日健康信息-----------------------------------------------------------------------

# @daily_health_info.handle()
# async def _(event: MessageEvent):
#     path = Path(XDU_SUPPORT_PATH, 'Ehall.txt')
#     flag, users = read_data(path)
#     users_id = [x[0] for x in users]
#     user_id = str(event.user_id)
#     if flag:
#         if user_id in users_id:
#             username = users[users_id.index(user_id)][1]
#             password = des_descrypt(
#                 users[users_id.index(user_id)][2], DES_KEY).decode()
#             message = punch_daily_health(username, password)
#             await chenwuwanjian.finish(message=f'[{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}] {message}')
#         else:
#             await chenwuwanjian.finish("您没有订阅学生健康信息功能，请先订阅再进行查看",)
#     else:
#         await chenwuwanjian.finish("获取数据失败，请联系管理员")
#
#
# # 定时8
# @scheduler.scheduled_job("cron", hour="8", month="2-7,9-12")
# async def run_at_8_every_day():
#     bot = nonebot.get_bot()
#     path = Path(XDU_SUPPORT_PATH, 'Ehall.txt')
#     flag, users = read_data(path)
#     if flag:
#         for user in users:
#             message = punch_daily_health(user[1], des_descrypt(user[2], DES_KEY).decode())
#             await bot.send_private_msg(user_id=int(user[0]),
#                                        message=f'[{datetime.now().strftime("%d/%m/%Y %H:%M:%S")}] {message}')
#     else:
#         await bot.send_private_msg(user_id=int(superusers[0]),
#                                    message='学生健康打卡读取数据失败，快维修')

# 体育打卡---------------------------------------------------------------------------


# # 定时每10分钟查一次
# @scheduler.scheduled_job("cron", minute="*/10", hour="7-22", month="2-7,9-12")
# async def run_every_10_minutes():
#     bot = nonebot.get_bot()
#     path = Path(XDU_SUPPORT_PATH, "Sports.txt")
#     flag, users = read_data(path)
#     if flag:
#         for user in users:
#             ses = SportsSession(user[1], des_descrypt(user[2], DES_KEY).decode())
#             flag, res = cron_check(ses, user[1])
#             if not flag:
#                 await asyncio.sleep(1)
#                 await bot.send_private_msg(user_id=int(user[0]), message=res)
#     else:
# await bot.send_private_msg(user_id=int(superusers[0]),
# message="体育打卡报时任务出错啦，请及时检查")


@sport_punch.handle()
async def _(event: MessageEvent):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Sports.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        ses = SportsSession(username, password)
        flag, res = get_sport_record(ses, username)
        await sport_punch.send(res)
        if flag:
            path = Path(XDU_SUPPORT_PATH, "Sports.txt")
            flag, users = read_data(path)
            if flag:
                users_id = [x[0] for x in users]
                users.pop(users_id.index(user_id))
                if write_data(path, users):
                    await sport_punch.finish(f"已经取消体育打卡功能的订阅啦！")
                else:
                    await sport_punch.finish(f"取消体育打卡订阅失败，请联系管理员")
            else:
                await sport_punch.finish("读取信息出错，请及时联系管理员")
        else:
            await sport_punch.finish("打卡还未到次数哦，请继续加油！")
    else:
        await sport_punch.finish("请先订阅体育打卡功能，再进行查询")

# 课表查询---------------------------------------------------------------------------


@update_timetable.handle()
async def _(event: MessageEvent):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()

        ses = EhallSession(username, password)
        ses.use_app(4770397878132218)
        get_timetable(ses, username, XDU_SUPPORT_PATH)

        await update_timetable.finish("课表更新成功，启动自动提醒")
    else:
        await update_timetable.finish("请先订阅课表提醒功能，再进行更新")


@timetable.handle()
async def _(event: MessageEvent):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    message = ""
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        if not os.path.exists(
            os.path.join(
                XDU_SUPPORT_PATH,
                f'{username}-remake.json')):
            await timetable.send("未找到本地课表，正在进行在线爬取并储存，请稍等", at_sender=True)
            ses = EhallSession(username, password)
            ses.use_app(4770397878132218)
            get_timetable(ses, username, XDU_SUPPORT_PATH)
            await timetable.send("课表更新完成，启动自动提醒，稍后返回数据", at_sender=True)
        if datetime.now().hour > 20:
            message += get_whole_day_course(username,
                                            TIME_SCHED, XDU_SUPPORT_PATH, 1)
        else:
            message += get_whole_day_course(username,
                                            TIME_SCHED, XDU_SUPPORT_PATH)
        await timetable.finish(message)
    else:
        await timetable.finish("请先订阅课表提醒功能，再进行查询")


@scheduler.scheduled_job("cron", hour="8", month="2-7,9-12")
async def run_at_8():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_next_course(user[1], XDU_SUPPORT_PATH)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)
    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')


@scheduler.scheduled_job("cron", minute="55", hour="9", month="2-7,9-12")
async def run_at_9():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_next_course(user[1], XDU_SUPPORT_PATH)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)
    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')


@scheduler.scheduled_job("cron", minute="30", hour="13", month="2-7,9-12")
async def run_at_13():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_next_course(user[1], XDU_SUPPORT_PATH)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)
    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')


@scheduler.scheduled_job("cron", minute="25", hour="15", month="2-7,9-12")
async def run_at_15():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_next_course(user[1], XDU_SUPPORT_PATH)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)
    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')


@scheduler.scheduled_job("cron", minute="30", hour="18", month="2-7,9-12")
async def run_at_18():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_next_course(user[1], XDU_SUPPORT_PATH)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)
    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')


@scheduler.scheduled_job("cron", hour="22", month="2-7,9-12")
async def run_at_22():
    bot = nonebot.get_bot()
    path = Path(XDU_SUPPORT_PATH, "Ehall.txt")
    flag, users = read_data(path)
    if flag:
        for user in users:
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f'{user[1]}-remake.json')):
                message = get_whole_day_course(
                    user[1], TIME_SCHED, XDU_SUPPORT_PATH, 1)
                if message:
                    await bot.send_private_msg(user_id=int(user[0]), message=message)

    else:
        await bot.send_private_msg(user_id=int(superusers[0]),
                                   message='课表提醒读取数据失败，快维修')

# 马原训练---------------------------------------------------------------------------


@mayuan.handle()
async def handle(state: T_State, args: Message = CommandArg()):
    msg = args.extract_plain_text().strip()
    if msg:
        if msg[0] == "单选":
            res, ans, _type = get_question(1)
        elif msg[0] == "多选":
            res, ans, _type = get_question(2)
        else:
            res, ans, _type = get_question(3)
    else:
        res, ans, _type = get_question(3)
    state["ans"] = ans
    await mayuan.send(_type + res)


@mayuan.got("user_ans", prompt="请在30秒内作答，格式为小写")
async def _(event: MessageEvent, state: T_State, user_ans: str = ArgStr("user_ans")):
    ans = state["ans"]
    path = Path(XDU_SUPPORT_PATH, "MY.txt")
    (flag, users) = read_data(path)
    # qq_id 答对总个数 答题总个数
    user_id = str(event.user_id)
    users_id = [x[0] for x in users]
    if user_id in users_id:
        current_data = users[users_id.index(user_id)]
        current_all = str(int(current_data[2]) + 1)
        if user_ans.upper() == ans:
            current_correct = str(int(current_data[1]) + 1)
            res_after_ans = "恭喜您回答正确\n"
        else:
            current_correct = current_data[1]
            res_after_ans = f"很遗憾回答错误，正确答案是{ans}\n"
        users[users_id.index(user_id)] = [
            user_id, current_correct, current_all]
        res_after_ans += "****************\n"
        res_after_ans += f"您当前的答题总数为{current_all}\n"
        res_after_ans += f"答对题目总数为{current_correct}\n"
        res_after_ans += f"正确率为{round(int(current_correct)/int(current_all),3)*100}%"
    else:
        current_all = "1"
        if user_ans.upper() == ans:
            current_correct = "1"
            res_after_ans = "恭喜您回答正确\n"
        else:
            current_correct = "0"
            res_after_ans = f"很遗憾回答错误，正确答案是{ans}\n"
        users.append([user_id, current_correct, current_all])
        res_after_ans += "****************\n"
        res_after_ans += f"您当前的答题总数为{current_all}\n"
        res_after_ans += f"答对题目总数为{current_correct}\n"
        res_after_ans += f"正确率为{round(int(current_correct) / int(current_all), 3) * 100}%"
    _ = write_data(path, users)
    await mayuan.finish(res_after_ans)

# 空闲教室查询------------------------------------------------------------------------


@stop_classroom.handle()
async def _(event: MessageEvent, state: T_State, args: Message = CommandArg()):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        msg = args.extract_plain_text().strip().split(" ")
        if msg:
            msg_ = msg[0].split("-")
            if len(msg_) != 2 or msg_[0] not in [
                    "A", "B", "C", "D", "EI", "EII", "EIII", "信远I", "信远II", "信远III"]:
                await stop_classroom.finish("教室格式有误，例如B-108，信远I-108")
            else:
                state["stoproom"] = msg[0]
    else:
        await stop_classroom.finish("请先订阅空闲教室功能，再进行反馈")


@stop_classroom.got("stoproom", prompt="请输入需要补充的停止教室")
async def _(stoproom: str = ArgStr("stoproom")):
    stoproom_ = stoproom.split("-")
    if len(stoproom_) != 2 or stoproom_[0] not in [
            "A", "B", "C", "D", "EI", "EII", "EIII", "信远I", "信远II", "信远III"]:
        await stop_classroom.reject_arg("stoproom", prompt="教室格式有误，例如B-108，信远I-108,请检查输入")
    else:
        if os.path.exists(
            os.path.join(
                XDU_SUPPORT_PATH,
                "stop_classroom.txt")):
            with open(os.path.join(XDU_SUPPORT_PATH, "stop_classroom.txt"), "r", encoding="utf-8") as f:
                stoprooms = f.readlines()
        else:
            stoprooms = []
        stoprooms.append(stoproom)
        with open(os.path.join(XDU_SUPPORT_PATH, "stop_classroom.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(stoprooms))
        await stop_classroom.finish(f"已经将教室{stoproom}添加到停止教室列表中，感谢您提供帮助，相信我们的服务会越来越好")


@idle_classroom_query.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State, args: Message = CommandArg()):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    message = []
    app_id = 4768402106681759
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        ses = EhallSession(username, password)
        ses.use_app(app_id)
        if not os.path.exists(
            os.path.join(
                XDU_SUPPORT_PATH,
                "teaching_buildings.txt")):
            teaching_buildings = get_teaching_buildings(ses)
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", "teaching_buildings.txt"), 'w', encoding="utf-8") as f:
                f.write(str(teaching_buildings))
        else:
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", "teaching_buildings.txt"), 'r', encoding="utf-8") as f:
                teaching_buildings = eval(f.read())
        buildings = [x[0] for x in teaching_buildings]
        msg = args.extract_plain_text().strip().split(" ")
        if len(msg) == 1 and msg[0] in buildings:
            state["build"] = msg[0]
        elif len(msg) == 2:
            if msg[0] in buildings:
                state["build"] = msg[0]
            try:
                time_select = jio.parse_time(
                    msg[1], time_base=time.time()).get("time")[0].split(" ")[0]
                state["time_select"] = time_select
            except ValueError:
                pass
        else:
            message.append(MessageSegment.text("南校区的教学楼有:"))
            for build in teaching_buildings:
                message.append(MessageSegment.text(f"{build[0]}"))
            await send_forward_msg(bot, event, name="XDU小助手", uin=bot.self_id, msgs=message)
        state["ses"] = ses
        state["buildings"] = teaching_buildings
    else:
        await timetable.finish("请先订阅空闲教室功能，再进行查询")


@idle_classroom_query.got("build", prompt="请输入您要查找的教学楼名称")
async def _(state: T_State, build: str = ArgStr("build")):
    if build in ["取消", "算了"]:
        await idle_classroom_query.finish("已取消本次操作")
    ses = state["ses"]
    teaching_buildings = state["buildings"]
    buildings = [x[0] for x in teaching_buildings]
    if build in buildings:
        if not os.path.exists(
            os.path.join(
                XDU_SUPPORT_PATH,
                f"{build}-classroom.txt")):
            rooms = get_classroom(
                ses, teaching_buildings[buildings.index(build)][1])
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", f"{build}-classroom.txt"), 'w', encoding='utf-8') as f:
                f.write(str(rooms))
        else:
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", f"{build}-classroom.txt"), 'r', encoding='utf-8') as f:
                rooms = eval(f.read())

        state["rooms"] = rooms
        state["ses"] = ses
        state["build"] = build
    else:
        await idle_classroom_query.finish("您输入的教学楼名称有误，请检查输入")


@idle_classroom_query.got("time_select", prompt="请输入查询日期,支持输入模糊文字如'下周四'或'这周三'")
async def _(event: MessageEvent, state: T_State, time_selector: str = ArgStr("time_select")):
    if time_selector in ["取消", "算了"]:
        await idle_classroom_query.finish("已取消本次操作")
    try:
        time_ = jio.parse_time(
            time_selector,
            time_base=time.time()).get("time")[0].split(" ")[0]
        ses = state["ses"]
        rooms = state["rooms"]
        build = state["build"]
        teaching_buildings = state["buildings"]
        buildings = [x[0] for x in teaching_buildings]
        if not os.path.exists(
            os.path.join(
                XDU_SUPPORT_PATH,
                "idle_classroom_query",
                f"{time_}_{build}_idle_rooms.txt")):
            if os.path.exists(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    "stop_classroom.txt")):
                with open(os.path.join(XDU_SUPPORT_PATH, "stop_classroom.txt"), "r", encoding="utf-8") as f:
                    stoprooms = f.readlines()
            else:
                stoprooms = []
            result = await get_idle_classroom(ses, rooms, time_, stoprooms)
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", f'{time_}_{build}_idle_rooms.txt'), 'w', encoding='utf-8') as f:
                f.write(str(result))
        else:
            with open(os.path.join(XDU_SUPPORT_PATH, "idle_classroom_query", f'{time_}_{build}_idle_rooms.txt'), 'r', encoding='utf-8') as f:
                result = eval(f.read())
        flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
        users_id = [x[0] for x in users]
        user_id = str(event.user_id)
        if user_id in users_id:
            username = users[users_id.index(user_id)][1]
            password = des_descrypt(
                users[users_id.index(user_id)][2], DES_KEY).decode()
            if not os.path.exists(
                    os.path.join(
                        XDU_SUPPORT_PATH,
                        f'{username}-remake.json')):
                await timetable.send("未找到本地课表，正在进行在线爬取并储存，请稍等", at_sender=True)
                ses = EhallSession(username, password)
                ses.use_app(4770397878132218)
                get_timetable(ses, username, XDU_SUPPORT_PATH)
                await timetable.send("课表更新完成，启动自动分析，稍后返回数据", at_sender=True)
            with open(os.path.join(XDU_SUPPORT_PATH, f"{username}-remake.json"), "r", encoding="utf-8") as f:
                courses = json.loads(f.read())
        message = analyse_best_idle_room(
            result, courses, time_, teaching_buildings[buildings.index(build)][1])
        await idle_classroom_query.finish(message)
    except ValueError:
        await idle_classroom_query.reject_arg("time_select", prompt="输入日期无法识别，请检查输入. 取消操作请回复'取消'或'算了'")


# AED-------------------------------------------------------------------------------


@aed_search.handle()
async def _(state: T_State):
    await aed_search.send("收到请求,欢迎使用AED查询，南北校区均适用。请按照操作提示进行操作以尽快获得位置数据")
    await asyncio.sleep(1)
    if not SK:
        await aed_search.send("由于未配置SK，因此只能返回文字数据")
        state["pos"] = " "


@aed_search.got("pos", prompt=("点击QQ右下角的加号'+'，依次点击'位置','发送位置','发送'"))
async def _(state: T_State, pos: Message = Arg("pos")):
    pos = str(pos).replace(
        "&amp;",
        "&").replace(
        "&#44;",
        ",").replace(
            "&#91;",
            "[").replace(
                "&#93;",
        "]")
    pos = re.sub("\\[\\[位置].*?]请使用最新版本手机QQ查看", "", pos)
    lat = ""
    lng = ""
    try:
        data = json.loads(pos[14:-1])
        lat += data["meta"]["Location.Search"]["lat"]
        lng += data["meta"]["Location.Search"]["lng"]
    except BaseException:
        pass
    if not lng:
        _, _, aed_infos = get_min_distance_aed()
        if SK:
            temp = "获取位置失败，但仍为您推荐预设地点:\n"
        else:
            temp = "已获取推荐的AED地点:\n"
        cnt = 0
        for info in aed_infos:
            cnt += 1
            temp += f"{cnt}. 位于{info['campus']}{info['loc']},{info['description']}\n"
        temp += "除以上信息外，每栋宿舍楼的2楼都有除颤仪配备，如有需要可以联系宿管询问\n\n请选择AED序号以获取发送位置信息"
        await aed_search.send(temp)
        state["infos"] = aed_infos
        state["max_num"] = cnt
        if not SK:
            state["num"] = 1
        await asyncio.sleep(0.5)
    else:
        aed_min_dist, min_dist, _ = get_min_distance_aed(lat, lng)
        await aed_search.send(f"获取位置成功，已找到最近的AED，距离约{int(min_dist)}米,位于{aed_min_dist['campus']} {aed_min_dist['loc']},{aed_min_dist['description']}。\n即将发送定位")
        state["num"] = 1
        state["infos"] = [aed_min_dist]
        state["max_num"] = 2
        state["lat"] = lat
        state["lng"] = lng
        await asyncio.sleep(0.5)


@aed_search.got("num")
async def _(state: T_State, num: str = ArgStr("num")):
    if SK:
        max_num = state["max_num"]
        if num not in [str(x) for x in range(max_num)]:
            await aed_search.finish("输入的数字超出了范围，请重新操作")
        aed_infos = state["infos"]
        num = int(num)
        info = aed_infos[num - 1]
        if max_num == 2:
            now_lat = state["lat"]
            now_lng = state["lng"]
            url = get_url_routeplan(
                now_lat,
                now_lng,
                info["lat"],
                info["lng"],
                SK,
                appname)
        else:
            url = get_url_marker(info["lat"], info["lng"], SK, appname)

        message = MessageSegment.share(
            url,
            title="腾讯地图",
            content=info["loc"] +
            "_" +
            info["description"])
        await aed_search.send(message)
    await asyncio.sleep(1)
    await aed_search.finish("找到AED除颤仪后请按照AED语音提示操作，注意与心肺复苏相急救结合使用。基本步骤如下:\n"
                            "1、确认患者状态：包括是否失去反应、失去呼吸等；\n"
                            "2、打开患者衣物裸露胸部，并根据标识将电极贴片贴在相应位置；\n"
                            "3、AED分析心率：避免接触患者，以免干扰对心率的分析；\n"
                            "4、当心率分析结果为室颤时，AED进行充电，充电完成后按下橙色按钮进行除颤，患者表现为全身瞬间抖动，之后需继续心肺复苏")


# 青年大学习--------------------------------------------------------------------------

@youthstudy.handle()
async def _(event: MessageEvent, state: T_State):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Youth.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        state["username"] = users[users_id.index(user_id)][1]
        state["password"] = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        ses = requests.session()
        get_verify(ses, base_path=XDU_SUPPORT_PATH)
        state["ses"] = ses
        await asyncio.sleep(0.5)
        await youthstudy.send(MessageSegment.image("file:///" / Path(XDU_SUPPORT_PATH) / "verify.png"))
        await asyncio.sleep(0.5)

    else:
        await youthstudy.finish("您暂未绑定青年大学习服务，请先绑定")


@youthstudy.got("verify", prompt="请输入验证码")
async def _(state: T_State, verify: str = ArgStr("verify")):
    username = state["username"]
    password = state["password"]
    ses = state["ses"]
    flag, msg = get_youthstudy_names(ses, verify, username, password)
    if flag:
        await youthstudy.finish(msg)
    else:
        await youthstudy.finish("登录失败，可能是验证码错误或账号密码失效，请重试或检查账号密码")

# 成绩查询---------------------------------------------------------------------------------


@grade.handle()
async def _(event: MessageEvent, bot: Bot):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        ses = EhallSession(username, password)
        ses.use_app(4768574631264620)
        msg, res = get_grade(ses)
        await grade.send(res + "\n计算公式为\nsum(必修学分*必修课分数)/sum(必修学分)" + "\n\n" + "下面为近两学期成绩")
        await asyncio.sleep(1)
        await send_forward_msg(bot, event, "XD小助手", str(event.user_id), msg)
    else:
        await grade.finish("请先订阅成绩查询功能，再进行更新")

# 考试查询-----------------------------------------------------------------------------------


@examination.handle()
async def _(event: MessageEvent, bot: Bot, args: Message = CommandArg()):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'Ehall.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        username = users[users_id.index(user_id)][1]
        password = des_descrypt(
            users[users_id.index(user_id)][2], DES_KEY).decode()
        ses = EhallSession(username, password)
        msg = args.extract_plain_text().strip().split(" ")
        if msg and msg[0] in ["上学期", "上一学期", "前一学期"]:
            term, examtimes = get_examtime(1, ses)
        else:
            term, examtimes = get_examtime(0, ses)
        examed = []
        examed.append(f"{term}学期的已完成考试")
        unexamed = []
        unexamed.append(f"{term}学期的未完成考试安排为")
        for examtime in examtimes:
            examtime_day = datetime.strptime(
                examtime["KSSJMS"].split(" ")[0], "%Y-%m-%d")
            timenow = datetime.strptime(
                datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            if examtime_day - timenow >= timedelta(days=0):
                unexamed.append(
                    f"在{examtime['KSSJMS']}\n****************\n你有一门{examtime['KCM']}的考试\n****************\n在{examtime['JASDM']}教室，座号为{examtime['ZWH']}\n****************\n任课教师为{examtime['ZJJSXM']}")
            else:
                examed.append(f"{examtime['KCM']}")
        await send_forward_msg(bot, event, "XD小助手", str(event.user_id), unexamed + examed)
    else:
        await examination.finish("请先订阅考试查询功能,再进行查询")
# 提醒记事------------------------------------------------------------------------------------


@remind.handle()
async def _(event: MessageEvent, state: T_State, args: Message = CommandArg()):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'TX.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        msg = args.extract_plain_text().strip().split(" ")
        if msg and msg[0] != "":
            if len(msg) == 1:
                event_name = get_eventname("提醒" + msg[0])
                if event_name:
                    state["item"] = event_name
            for m in msg:
                try:
                    m_ = jio.parse_time(
                        m,
                        time_base=time.time()).get("time")[0].split(" ")[0]
                    state["ddl"] = m_
                except:
                    event_name = get_eventname("提醒" + m)
                    if event_name:
                        state["item"] = event_name
    else:
        await remind.finish("请先订阅提醒功能，再进行添加")


@remind.got("item", prompt="请输入要完成的事项")
async def _(event: MessageEvent, state: T_State, item: str = ArgStr("item")):
    if item in ["取消", "算了"]:
        await remind.finish("已取消本次操作")
    user_id = str(event.user_id)
    _, items = read_data(
        Path(
            os.path.join(
                XDU_SUPPORT_PATH, f"{user_id}todolist.txt")))
    state["items"] = items


@remind.got("ddl", prompt="请输入截止时间")
async def _(event: MessageEvent, state: T_State, ddl: str = ArgStr("ddl"), item: str = ArgStr("item")):
    user_id = str(event.user_id)
    items = state["items"]
    if ddl in ["取消", "算了"]:
        await remind.finish("已取消本次操作")
    try:
        ddl_ = jio.parse_time(
            ddl,
            time_base=time.time()).get("time")[0].split(" ")[0]
        item_name = [x[0] for x in items]
        if item in item_name and ddl_ == items[item_name.index(item)][1]:
            await remind.finish(f"已经添加过截止日期为{ddl_}的{item}啦，不用再重复添加啦！")
        items.append([item, ddl_])
        _ = write_data(
            Path(
                os.path.join(
                    XDU_SUPPORT_PATH,
                    f"{user_id}todolist.txt")),
            items)
        timenow = datetime.strptime(
            datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        ans = [
            f"{i}将在{d}截止,仅剩{(datetime.strptime(d, '%Y-%m-%d') - timenow).days}天" for i,
            d in items]
        await asyncio.sleep(1)
        msg = "添加成功！目前您仍有以下待办：\n"
        for i in range(len(ans)):
            msg += f"****************\n{i}. {ans[i]}\n"
        await remind.finish(msg)
    except ValueError:
        await idle_classroom_query.reject_arg("time_select", prompt="输入日期无法识别，请检查并重新输入. 取消操作请回复'取消'或'算了'")


@remind_finish.handle()
async def _(event: MessageEvent, state: T_State, args: Message = CommandArg()):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'TX.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    if user_id in users_id:
        _, items = read_data(
            Path(
                os.path.join(
                    XDU_SUPPORT_PATH, f"{user_id}todolist.txt")))
        if not items:
            await remind_finish.finish("已经没有ddl啦，无需再进行删除哦~")
        msg = args.extract_plain_text().strip().split(" ")
        if msg:
            try:
                int(msg[0])
                state["item"] = int(msg[0])
            except BaseException:
                state["item"] = msg[0]
            state["items"] = items
        else:
            ans = [f"{i}将在{d}截止" for i, d in items]
            await asyncio.sleep(1)
            msg = "目前您仍有以下待办：\n"
            for i in range(len(ans)):
                msg += f"****************\n{i}. {ans[i]}\n"
            await remind_finish.send(msg)
    else:
        await remind.finish("您暂未订阅提醒功能哦~")


@remind_finish.got("item", prompt="请输入您完成的事项名称或序号")
async def _(event: MessageEvent, state: T_State, item: str = ArgStr("item")):
    user_id = str(event.user_id)
    items = state["items"]
    if item in ["取消", "算了"]:
        await remind_finish.finish("已取消本次操作")
    try:
        item = int(item)
    except BaseException:
        pass
    if isinstance(item, int):
        if item < len(items):
            removed_item = items.pop(item)
            write_data(
                Path(
                    os.path.join(
                        XDU_SUPPORT_PATH,
                        f"{user_id}todolist.txt")),
                items)
            await remind_finish.finish(f"成功移除事项{removed_item[0]}")
        else:
            await remind_finish.finish(f"不存在编号为{item}的事项，请检查输入")
    else:
        item_name = [x[0] for x in items]
        if item in item_name:
            removed_item = items.pop(item_name.index(item))
            write_data(
                Path(
                    os.path.join(
                        XDU_SUPPORT_PATH,
                        f"{user_id}todolist.txt")),
                items)
            await remind_finish.finish(f"成功移除事项{removed_item[0]}")
        else:
            await remind_finish.finish(f"没有名称为{item}的事项，请检查输入")


@remind_poke.handle()
async def _(event: PokeNotifyEvent):
    flag, users = read_data(Path(XDU_SUPPORT_PATH, 'TX.txt'))
    users_id = [x[0] for x in users]
    user_id = str(event.user_id)
    await asyncio.sleep(1)
    if user_id in users_id:
        _, items = read_data(
            Path(
                os.path.join(
                    XDU_SUPPORT_PATH, f"{user_id}todolist.txt")))
        await asyncio.sleep(1)
        if not items:
            await remind_poke.finish("您暂时没有待办事项哦~")
        else:
            timenow = datetime.strptime(
                datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            ans = [
                f"{i}将在{d}截止,仅剩{(datetime.strptime(d, '%Y-%m-%d')-timenow).days}天" for i,
                d in items]
            msg = "目前您仍有以下待办：\n"
            for i in range(len(ans)):
                msg += f"****************\n{i}. {ans[i]}\n"
            await remind_poke.finish(msg)
    else:
        await remind.finish("您暂未订阅提醒功能哦~")


@scheduler.scheduled_job("cron", hour="22", minute="5")
async def run_at_22_30():
    bot = nonebot.get_bot()
    flag, users_ = read_data(Path(XDU_SUPPORT_PATH, 'TX.txt'))
    users_id = [x[0] for x in users_]
    for user in users_id:
        if os.path.exists(
                Path(
                    os.path.join(
                XDU_SUPPORT_PATH,
                f"{user}todolist.txt"))):
            _, items = read_data(
                Path(
                    os.path.join(
                        XDU_SUPPORT_PATH, f"{user}todolist.txt")))
            timenow = datetime.strptime(
                datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
            await asyncio.sleep(1)
            msg = "目前您有以下待办距离ddl时间较紧，明天请合理安排时间：\n"
            overtime = []
            intime = []
            for i in range(len(items)):
                flag2 = 0
                ddltime = datetime.strptime(items[i][1], '%Y-%m-%d')
                resttime = ddltime - timenow
                if timedelta(days=0) <= resttime < timedelta(days=5):
                    msg += f"****************\n{items[i][0]}距离截止日期{items[i][1]}仅剩余{resttime.days}天\n"
                elif resttime < timedelta(days=0):
                    overtime.append(items[i][0])
                    flag2 = 1
                if flag2 == 0:
                    intime.append(items[i])
            if overtime:
                msg += "****************\n有以下事项已过期，已经自动删除，请注意！\n"
                msg += "\n".join(overtime)
                _ = write_data(
                    Path(
                        os.path.join(
                            XDU_SUPPORT_PATH,
                            f"{user}todolist.txt")),
                    intime)
            await bot.send_private_msg(user_id=int(user), message=msg)

# 命令预处理


@cmd.handle()
async def _(event: MessageEvent, bot: Bot, msg: Message = EventPlainText()):
    msg_event = get_handle_event(msg, event)
    if msg_event:
        asyncio.create_task(handle_event(bot, msg_event))


# 文档操作----------------------------------------------------------------------------


def write_data(path: Path, data: list) -> bool:
    try:
        if data:
            flag = 0
            for info in data:
                if flag == 0:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(' '.join(info))
                    flag = 1
                elif flag == 1:
                    with open(path, 'a', encoding='utf-8') as f:
                        f.write('\n' + (' '.join(info)))
        else:
            with open(path, 'w') as f:
                f.write('')
        return STATE_OK
    except BaseException as e:
        print(e)
        return STATE_ERROR


def read_data(path: Path) -> (bool, list):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = f.readlines()
        if data:
            infos = [x.split() for x in data]
        else:
            infos = []

        return STATE_OK, infos
    except BaseException as e:
        print(e)
        return STATE_ERROR, []

# 合并转发---------------------------------------------------------------------------------------


async def send_forward_msg(
    bot: Bot,
    event: MessageEvent,
    name: str,
    uin: str,
    msgs: List[Union[MessageSegment, Message, str]],
) -> dict:
    def to_json(msg: Union[MessageSegment, Message, str]):
        return {
            "type": "node",
            "data": {
                "name": name,
                "uin": uin,
                "content": msg}}

    messages = [to_json(msg) for msg in msgs]
    if isinstance(event, GroupMessageEvent):
        return await bot.call_api(
            "send_group_forward_msg", group_id=event.group_id, messages=messages
        )
    else:
        return await bot.call_api(
            "send_private_forward_msg", user_id=event.user_id, messages=messages
        )

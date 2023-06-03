import datetime
import json
import os
import requests
from bs4 import BeautifulSoup
import numpy as np
from typing import List


def reqres(LoginID: str, Password: str) -> List:
    login_url = "http://wlsy.xidian.edu.cn/PhyEWS/default.aspx?ReturnUrl=/PhyEws/student/course.aspx"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Content-Length": "591",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "wlsy.xidian.edu.cn",
        "Origin": "http://wlsy.xidian.edu.cn",
        "Pragma": "no-cache",
        "Referer": "http://wlsy.xidian.edu.cn/PhyEWS/default.aspx?ReturnUrl=%2fPhyEws%2fstudent%2fcourse.aspx",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.34",
    }

    data = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": "/wEPDwUKMTEzNzM0MjM0OWQYAQUeX19Db250cm9sc1JlcXVpcmVQb3N0QmFja0tleV9fFgEFD2xvZ2luMSRidG5Mb2dpbkOuzGVaztce4Ict7jsIJ0F5pUDb+smSbCCrNVSBlPML",
        "__VIEWSTATEGENERATOR": "EE008CD9",
        "__EVENTVALIDATION": "/wEdAAcKecdPGDB+fW8Tyghx7AeSpOzeiNZ7aaEg5p6LqSa9cODI2bZwNtRxUKPkisVLf8l8Vv4WhRVIIhZlyYNJO+ySrDKOhP+/YMNbVIh74hA2rCYnBBSTsX9SjxiYNNk+5kglM+6pGIq22Oi5mNu6u6eC2WEBfKAmATKwSpsOL/PNcRyi9l8Dnp6JamksyAzjhW4=",
        "login1$StuLoginID": LoginID,
        "login1$StuPassword": Password,
        "login1$UserRole": "Student",
        "login1$btnLogin.x": "37",
        "login1$btnLogin.y": "12",
    }

    session = requests.Session()
    response = session.post(login_url, headers=headers, data=data)

    # 发送选课页面请求
    response = session.get(
        "http://wlsy.xidian.edu.cn/PhyEWS/student/select.aspx")

    html = response.text
    soup = BeautifulSoup(html, 'html.parser')

    experiments = []

    for tr in soup.find_all('tr'):
        row = []
        for td in tr.find_all('td'):
            row.append(td.get_text().strip())
        if len(row) > 0:
            experiments.append(row)
    experiments = experiments[4:13]
    return experiments


def find_conflicts(schedule: json) -> str:
    conflicts = []
    for date, courses in schedule.items():
        has_3_and_5 = "3" in courses and "5" in courses
        has_4_and_6 = "4" in courses and "6" in courses
        if has_3_and_5 or has_4_and_6:
            conflict_courses = []
            if has_3_and_5:
                conflict_courses.append(str(courses["3"]["name"] + ' 和'))
                conflict_courses.append(str(courses["5"]["name"]))
            if has_4_and_6:
                conflict_courses.append(str(courses["4"]["name"] + ' 和'))
                conflict_courses.append(str(courses["6"]["name"]))
            conflicts.append([date, *conflict_courses])
    conflicts_str = '\n'.join(['\t'.join(c) for c in conflicts])
    return conflicts_str


def is_wright(user: str, passwd: str) -> bool:
    data = reqres(user, passwd)
    # 如果正确data中不会有['学生教师']
    return not ['学生教师'] in data


def getwrit_pe(user: str, passwd: str, path: str) -> (str, str, bool):
    write_ = bool()
    data = reqres(user, passwd)
    # 处理成json并写入到本地课表
    ####################################################
    data_np = np.array(data)
    # print(data_np)
    data_np = data_np[:, [1, 3, 4, 5]]
    data_np[:, 1] = [item[5:] for item in data_np[:, 1]]

    for row in data_np:
        row[1] = row[1].replace('18:30-20:45', '6').replace('15:55-18:10', '5')
        date_str = row[-2]  # 获取子列表中的最后一个元素
        date_obj = datetime.datetime.strptime(
            date_str, '%m/%d/%Y')  # 将字符串转换为datetime对象
        date_str_new = date_obj.strftime('%Y-%m-%d')  # 将datetime对象转换为字符串
        row[-2] = date_str_new  # 将新的字符串格式更新到原来的子列表中的最后一个元素
    data_dict = {}
    for row in data_np:
        date = row[2]
        course_info = {
            "name": row[0],
            "location": row[3]
        }
        if date in data_dict:
            data_dict[date][row[1]] = course_info
        else:
            data_dict[date] = {row[1]: course_info}
    conflicts = str()
    try:
        # 读取json课表文件中的内容
        with open(path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # 将data_dict添加到json_data中
        for key in data_dict:
            if key in json_data:
                if isinstance(json_data[key], dict) and isinstance(data_dict[key], dict):
                    json_data[key].update(data_dict[key])
                elif isinstance(json_data[key], list) and isinstance(data_dict[key], list):
                    json_data[key].extend(data_dict[key])
                else:
                    json_data[key] = data_dict[key]
            else:
                json_data[key] = data_dict[key]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        # 写入到临时变量后，判断是否有课程冲突存在
        #################################################
        conflicts = find_conflicts(json_data)
        #################################################

        # 将更新后的json_data写回json课表文件中
        with open(path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False)
        write_ = True
    except (FileNotFoundError, json.JSONDecodeError, IOError, TypeError):
        write_ = False
    # 处理成课表str信息，发送给用户
    #######################################################
    # 获取当前文件的绝对路径
    current_file_path = os.path.abspath(__file__)
    # 获取父目录路径
    parent_dir_path = os.path.dirname(current_file_path)
    with open(rf'{parent_dir_path}/class_ever.json', 'r', encoding='utf-8') as f:
        class_teacher = json.load(f)
    for each in data:
        key1 = each[1][0:-5]
        key2 = each[3]
        teacher = class_teacher[key1][key2]
        each.append(teacher)
    for row in data:
        del row[0], row[1], row[4]
        row[2] = row[2] + row[1]
        del row[1]
        row[0], row[1] = '*' + row[1] + '\n', '--' + row[0] + '\n'
        row[2] = '-----位置:' + row[2] + '\n'
        row[3] = '-----成绩:' + row[3] + '\n'
        row[4] = '-----归一成绩:' + row[4] + '\n'
        row[5] = '-----备注:' + row[5] + '\n'
        row[6] = '-----教师:' + row[6] + '\n'
        row.insert(3,row.pop(6))
    data_str = [[str(x) for x in row] for row in data]

    output_str = ''.join([''.join(row) for row in data_str])
    # 直接发给用户的信息，是否冲突，是否更新了课表提醒的课表
    return output_str, conflicts, write_

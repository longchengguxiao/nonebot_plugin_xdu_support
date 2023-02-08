<!-- markdownlint-disable MD033 MD041 -->
<p align="center">
  <img src="https://github.com/longchengguxiao/nonebot_plugin_xdu_support/blob/master/nonebot_plugin_xdu_support_logo.png" width="250" height="250" alt="nonebot_plugin_pvz">
</p>
<div align="center">

# nonebot_plugin_xdu_support

<!-- prettier-ignore-start -->
<!-- markdownlint-disable-next-line MD036 -->
_✨ 基于nonebot的XDU服务插件 ✨_
<!-- prettier-ignore-end -->

</div>

<p align="center">
    <a href="https://github.com/longchengguxiao/nonebot_plugin_xdu_support/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/longchengguxiao/nonebot_plugin_xdu_support" alt="license">
    </a>
    <a href="https://pypi.python.org/pypi/nonebot_plugin_xdu_support">
    <img src="https://img.shields.io/pypi/v/nonebot_plugin_xdu_support" alt="pypi">
    </a>
    <img src="https://img.shields.io/badge/python-3.8+-blue" alt="python">
    <br />
    <a href="https://onebot.dev/">
    <img src="https://img.shields.io/badge/OneBot-v11-black?style=social&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABABAMAAABYR2ztAAAAIVBMVEUAAAAAAAADAwMHBwceHh4UFBQNDQ0ZGRkoKCgvLy8iIiLWSdWYAAAAAXRSTlMAQObYZgAAAQVJREFUSMftlM0RgjAQhV+0ATYK6i1Xb+iMd0qgBEqgBEuwBOxU2QDKsjvojQPvkJ/ZL5sXkgWrFirK4MibYUdE3OR2nEpuKz1/q8CdNxNQgthZCXYVLjyoDQftaKuniHHWRnPh2GCUetR2/9HsMAXyUT4/3UHwtQT2AggSCGKeSAsFnxBIOuAggdh3AKTL7pDuCyABcMb0aQP7aM4AnAbc/wHwA5D2wDHTTe56gIIOUA/4YYV2e1sg713PXdZJAuncdZMAGkAukU9OAn40O849+0ornPwT93rphWF0mgAbauUrEOthlX8Zu7P5A6kZyKCJy75hhw1Mgr9RAUvX7A3csGqZegEdniCx30c3agAAAABJRU5ErkJggg==" alt="onebot">
    </a>
    <a href="https://jq.qq.com/?_wv=1027&k=SXLKmKJX">
    <img src="https://img.shields.io/badge/QQ%E7%BE%A4-719392400-orange?style=flat-square" alt="QQ Chat Group">
    </a>
</p>

## 说在前面

+ 请插件使用者仔细阅读此文档,确保能够正确理解命令。定时任务报错时会联系bot的superuser，因此一定要填好配置项才可以使用

+ 所有密码都经过**加密储存**，加密令牌可以[自定义](#自定义配置)，设置`DES_KEY`项。

+ 虽然对密码进行了加密处理，但是很遗憾，所有加密都是**可逆**的，如果不了解bot的主人请谨慎使用插件，**谨慎填写密码**。在进行功能订阅时可以回复'算了'或者'取消'来取消本次操作，或者在使用完功能后及时取消订阅该功能，以免造成不必要的损失

+ 请谨慎利用**记事本修改**数据保存的文件，这可能会导致插件运行出错

+ 对于插件问题可以提交issue或者pull_requests来进行交流

+ 对于本插件及本人下其他插件感兴趣的朋友可以添加QQ群聊（719392400）来对插件的发展给出建议以及测试

+ **用爱发电，请勿商用**

## 简介

Nonebot2插件，提供基础的西电校园服务，如课表提醒，体育打卡查询及提醒(暂未完善)，晨午晚检打卡，空闲教室查询和马原测试等功能。

## 安装

```buildoutcfg
从 nb_cli 安装
python -m nb_cli plugin install nonebot_plugin_xdu_support

或从 PyPI 安装
python -m pip install nonebot_plugin_xdu_support
```

## 使用

```buildoutcfg
在bot.py 中添加nonebot.load_plugin("nonebot_plugin_xdu_support")

以及配置好nonebot_plugin_apscheduler,否则定时任务无法顺利执行
```
配置部分可以参考[nonebot文档](https://v2.nonebot.dev/docs/advanced/scheduler)

## 详细用法

> 详细用法参见[使用文档](https://longchengguxiao.github.io/plugindoc/#/nonebot_plugin_xdu_support/README)

## 更新

<details>
<summary>展开/收起</summary>

### v0.3.7

+ 2023/02/07 更新学生健康信息，由[@cyk1464](https://github.com/cyk1464) 提供脚本

### v0.3.0

+ 2023/01/30 更新AED查询功能，结合路径给出最佳选择

### v0.2.9

+ 2023/01/29 爆肝解决一切已知问题，根本难不倒我

### v0.2.2

+ 2023/01/29 新增空闲教室查询功能，结合课表进行优化

### v0.1.6

+ 2023/01/28 使用暂无问题，修复了mknod报错

### v0.1.0

+ 2023/01/28 基础功能基本实现，选课模块以及体育打卡补缺提上日程

</details>

## 自定义配置

```buildoutcfg
对Python编程比较熟悉的使用者可以在 .env 文件中设置XDU_SUPPORT_PATH来选择存储位置，不设置即为默认位置

设置 DES_KEY 来更改加密秘钥，但要注意必须是8位的字符串，否则无法正常运行
```

## 特别感谢

感谢 [libxduauth](https://github.com/xdlinux/libxduauth) 项目提供模拟登陆

感谢 [xd_script](https://github.com/xdlinux/xidian-scripts) 项目提供参考，部分代码转化/改写自其中的脚本

感谢 [@cyk1464](https://github.com/cyk1464) 提供学生健康信息脚本

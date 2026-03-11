# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/11/01 15:00
# @File:        slack_message.py
# @Software:    PyCharm
# @Description: 发送脚本的执行信息到slack。
import os
from dataclasses import dataclass
from time import time

import httpx

from .logger import Logger

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Attachment:
    title: str = "任务状态"  # 附件的标题，通常用于简要描述附件的内容（例如：“任务状态”、“错误报告”）。
    text: str = None  # 附件的主要文本内容。它是附件中展示的详细信息，可以是错误消息、报告或任务描述等。
    fallback: str = None  # 备用文本，用于在 Slack 客户端无法渲染附件内容时显示。一般情况下，如果附件无法显示，则会显示这个字段的内容。
    color: str = "good"  # 附件的颜色，通常用来标识状态。可以是 `good`（绿色表示成功）、`warning`（黄色表示警告）、`danger`（红色表示错误）或自定义的十六进制颜色（如 `#FF5733`）。
    pretext: str = "爬虫执行情况："  # 附件内容前的文本，通常显示在附件的上方，作为附件的引导或背景信息。
    author_name: str = "default_author_name"  # 作者的名字，通常用于显示附件的创建者或负责人。
    author_link: str = None  # 作者链接，提供作者的个人主页、GitHub 页面或其他相关链接。
    author_icon: str = None  # 作者的头像图标，通常是一个 URL，指向作者的头像图片，用于个性化展示。
    fields: list = None  # 一个字段列表，包含多个 `Field` 对象。每个 `Field` 表示一条信息（如任务状态、抓取数量等），可以在附件中并排显示多个字段。
    footer: str = "爬虫消息机制"  # 页脚文本，通常用于显示附加信息（如版权信息、系统名称等）。
    footer_icon: str = None  # 页脚图标，通常是一个 URL，指向图标图片，显示在页脚旁边。
    ts: int = int(time())  # 时间戳，表示附件的创建时间，通常是 Unix 时间戳（从 1970 年 1 月 1 日到当前的秒数）。

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value}


@dataclass
class Field:
    title: str = None  # 字段的标题，用于简要描述字段的内容。
    value: str = None  # 字段的值，实际显示的内容。
    short: bool = False  # 控制字段是否紧凑显示。True 表示字段将占用一半行宽，多个字段可以并排显示；False 表示字段将占用整个行宽。
    emoji: bool = False  # 控制 `value` 字段是否支持 emoji，如果为 True，Slack 会将文本中的 emoji 表情符号渲染为实际的图标。
    mrkdwn: bool = False  # 控制 `value` 字段是否支持 Markdown 格式化。如果为 True，Slack 会解析并渲染 Markdown 语法（如粗体、斜体、链接等）。

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value}


class SlackMessage(Logger):
    name = 'SlackMessage'

    def __init__(self, *args, **kwargs):
        self._kwargs = {}
        self._kwargs.update(kwargs)
        self.base_path = kwargs.get('package_root_path', BASE_PATH)
        super().__init__(
            *args, **{
                "log_name": self.name,
                "log_dir": self._kwargs.get(
                    'log_dir',
                    os.path.join(
                        self.base_path,
                        'logs',
                        self.name
                    )
                ),
            }
        )

    def _send_message(self, payload):
        url = self._kwargs.get("url")

        headers = {
            "content-type": "application/json",
        }
        response = httpx.post(url, headers=headers, json=payload)
        return response.status_code == 200 and response.text == "ok"

    def send_message(self, attachment: Attachment | dict, fields: list[Field | dict], extra: dict = None):
        extra = extra or {}
        fields = [each.to_dict() if isinstance(each, Field) else each for each in fields if each]
        attachment.fields = fields
        attachment_ = attachment.to_dict() if isinstance(attachment, Attachment) else attachment
        attachment_.update(extra)
        payload = {
            "text": "爬虫任务执行报告",
            "attachments": [
                attachment_
            ]
        }
        self._send_message(payload)


if __name__ == '__main__':
    pass

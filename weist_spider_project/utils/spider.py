# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2026/-/- 00:00
# @File:        spider.py
# @Software:    PyCharm
# @Description: 模板文件
import asyncio
import json
import os
import re
import threading
import traceback
from dataclasses import is_dataclass
from time import time
from typing import Literal, final, Coroutine, Generator

import urllib3

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


async def async_func_test(cls, kw=None):
    async def check_upload_result(func_upload):
        async for item in func_upload():
            print(s if len(s := json.dumps(item) if isinstance(item, str) else item) < 300 else s[:300] + "...")

    project = cls(**(kw or {}))
    async with asyncio.TaskGroup() as tg:
        tg.create_task(project.process())
        tg.create_task(check_upload_result(project.upload_result))


def func_test(cls, kw=None):
    project = cls(**(kw or {}))
    for result in project.process():
        if isinstance(result, list):
            for item in result[project.name]:
                print(item)
        else:
            print(result)


def auto_execute_method(auto_exec_level: int = 1):
    """装饰器：标记需要自动执行的方法

    :param auto_exec_level: auto_exec_level>=0,auto_exec_level==0时不执行
    :return:
    """
    if auto_exec_level is None:
        auto_exec_level = 1
    if auto_exec_level < 0 or not isinstance(auto_exec_level, int):
        raise Exception(f"[def:auto_execute_method] auto_exec_level({auto_exec_level})")

    def wrapper(func):
        if auto_exec_level == 0:
            return func
        func._auto_exec = auto_exec_level  # 添加标志
        return func

    return wrapper


class BasedSpider(object):
    name = None
    log = None

    def __init__(self, *args, **kwargs):
        # ====内部配置====
        self._auto_perform_tasks = {}
        self._kwargs = {}
        self._kwargs.update(kwargs)
        self.exceptions = {}
        self.extra_params = self._kwargs.get("extra_params", {})
        # ====通用配置====
        self.spider_mode = kwargs.get('env', "local")
        self.log = kwargs.get('log')
        self.base_path = kwargs.get("root_package_path", BASE_PATH)
        self.fetch_proxies = kwargs.get('fetch_proxies')
        self.proxies = self.fetch_proxies(**self._kwargs.get('proxy_setting', {})) if self.fetch_proxies else None
        # ====初始化====
        self._scan_methods()

    @final
    def _scan_methods(self):
        """扫描类中的所有方法并根据标志决定是否自动执行"""
        for method_name in dir(self):
            if method_name.startswith("_"):  # 忽略以 "_" 开头的私有方法
                continue
            method = getattr(self, method_name)
            # print(method, hasattr(method, "_auto_exec"))
            if callable(method) and hasattr(method, "_auto_exec"):
                self._auto_perform_tasks[method] = getattr(method, "_auto_exec")
        self._auto_perform_tasks = dict(sorted(self._auto_perform_tasks.items(), key=lambda x: x[1]))

    def _print(self, msg: str, log_type: Literal["info", "warn", "error"] = "info", check_head=True):
        """
        打印字符串
        增加字符串首位提醒：
            - 字符串首位不是中括号加"对象"模式
        """
        if check_head and not re.match(r'^\[.*?] ', msg):
            msg = f"[{self.name}] {msg}"
        if self.log:
            log_dict = {
                "info": self.log.info,
                "warn": self.log.warning,
                "error": self.log.error,
            }
            log_dict[log_type](msg)
        else:
            print(msg)

    def json_action(self, path: str, obj: list | dict = None, action="load", encoding="utf-8"):
        if not path:
            self._print(f"[def:json_action] No path", "error")
            return {}
        if action == "load":
            if not os.path.exists(path):
                self._print(f"[def:json_action] File({path}) does not exist", "error")
                return {}
            with open(path, "r", encoding=encoding) as f:
                return json.load(f)
        if action == "save":
            if obj is None:
                self._print(f"[def:json_action] Saving path({path}) fail, not obj", "error")
                return {}
            with open(path, "w", encoding=encoding) as f:
                json.dump(obj, f, ensure_ascii=False, indent=4)
        return path


class AsyncSpider(BasedSpider):
    name = "async_spider"
    script_type = "async"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ====异步配置====
        self._is_uploading = True
        self._is_processing = True
        self._process_done = False
        self._lock = threading.Lock()
        self._task_group = []  # 核心运行任务组
        # ====上传缓存====
        self.slice_step = self._kwargs.get("upload_slice", 100)
        self.batch_upload = True
        self.upload_queue = None
        # ====初始化====
        self._init_task_group([
            self.perform_tasks(),
            self._check_process_status(),
        ])

    # ======================框架代码=========================
    def _init_task_group(self, task_or_group: list | Coroutine):
        (
            self._task_group.extend(task_or_group)
            if isinstance(task_or_group, list)
            else self._task_group.append(task_or_group)
        )

    async def _check_process_status(self):
        """ 异步检查运行状态
        信号机制，返回运行状态
        :yield: self._is_processing
        """
        while True:
            if not self._is_processing:
                if not self._process_done:
                    raise KeyboardInterrupt
                self._is_uploading = False
                break
            await asyncio.sleep(1)

    def re_execute(self):
        """ 重新执行接口
        初始化程序参数，需要将存储数据清空
        :return:
        """
        self.__init__(**self._kwargs)
        self._print(f"[{self.name}] re-execute finish")

    async def stop_process_async(self):
        """ 异步停止运行入口
        linux平台下，执行指令
            - kill -2 pid
        终止程序运行
        :return:
        """
        self._print(f"[{self.name}] stop process...")
        self._is_processing = False

    @final
    async def upload_result(self):
        """ 异步上传结果
        根据具体情况调整上传模式
        self.batch_upload 控制是否批量上传，为False时直接上传
        上传格式：
            {
                upload_obj: Any
            }
        :return:
        """
        self._print(f"[{self.name}] start upload result...")
        batch = []
        if not self.upload_queue:
            self.upload_queue = asyncio.Queue(maxsize=self.slice_step)
        while self._is_uploading or not self.upload_queue.empty():
            try:
                item = await asyncio.wait_for(self.upload_queue.get(), timeout=0.5)
                (
                    batch.append(item)
                    if self.batch_upload  # 是否批量上传
                    else (
                        yield
                        {self.name: item}  # 封装
                        if is_dataclass(item)  # 为dataclass时自动封装
                        else item  # 不封装
                    )
                )
                self.upload_queue.task_done()
            except asyncio.TimeoutError:
                pass
            if len(batch) >= self.slice_step:
                yield {self.name: batch}  # 封装数据
                batch = []

        if batch:
            yield {self.name: batch}
        self._print(f"[{self.name}] Upload result done")

    async def perform_tasks(self):
        """ 异步执行任务
        顺序执行的异步函数放在此执行
        :return:
        """
        for task in self._auto_perform_tasks.keys():
            await task()
        self._is_processing = False
        self._process_done = True

    @final
    async def process(self):
        """ 程序入口函数
        框架调用
        :return:
        """
        self._print(f"{f' [{self.name}:start] ':*^110}", check_head=False)
        self._print(f"Process start...")
        num_of_err = 0
        while self._is_uploading:
            if num_of_err > self._kwargs.get("num_of_err", 0):
                break
            try:
                async with asyncio.TaskGroup() as tg:
                    [tg.create_task(task) for task in self._task_group]
            except KeyboardInterrupt:
                # 中断程序
                self._is_processing = False
            except Exception as e:
                e_ = str(e)
                if e_.startswith(f"[{self.name}]"):
                    self._print(f"process error: [{e_}]")
                else:
                    traceback.print_exc()
                self.exceptions[f"{self.name}:{int(time())}"] = e_
                num_of_err += 1
        self._print(f"Process finish")
        self._is_uploading = False
        self._print(f"{f' [{self.name}:finish] ':*^110}", check_head=False)


class Spider(BasedSpider):
    name = "spider"
    script_type = "normal"
    log = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # ==========爬虫代码==========
    @final
    def process(self):
        self._print(f"{f' [{self.name}:start] ':*^110}", check_head=False)
        for task in self._auto_perform_tasks.keys():
            (yield from result) if isinstance(result := task(), Generator) else (yield result)
        self._print(f"{f' [{self.name}:finish] ':*^110}", check_head=False)

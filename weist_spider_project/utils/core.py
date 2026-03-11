# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/08/15 15:00
# @File:        core.py
# @Software:    PyCharm
# @Description: 爬虫框架文件
import asyncio
import importlib
import json
import os
import platform
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, is_dataclass
from datetime import datetime
from time import time
from typing import Any
from urllib.parse import urljoin

import requests

from .cliproxy import CliProxy
from .logger import Logger
from .mysql_db import DatabaseConnect
from .rocket_mq import MQClient
from .slack import Field, Attachment, SlackMessage
from .tools import fetch_proxies_from_qg, fetch_proxies_from_clash

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


@dataclass
class TaskStatus:
    Process: dict = field(default_factory=dict)
    ProcessThread: dict = field(default_factory=dict)
    ProcessAsync: dict = field(default_factory=dict)

    def to_result(self):
        return [
            *[not isinstance(v, int) for v in self.Process.values()],
            *[not isinstance(v, int) for v in self.ProcessThread.values()],
            *[not isinstance(v, int) for v in self.ProcessAsync.values()]
        ]


class InitParams(Logger):

    def __init__(self, *args, **kwargs):  # noqa
        # ===== 基础信息（不依赖配置）=====
        self.raw_kwargs = dict(kwargs)
        self.system = platform.system()  # 系统运行环境
        self.name = kwargs.get('name', 'DispatcherSpider')  # 继承子类名称
        self.base_path = kwargs.get('package_root_path', BASE_PATH)  # 项目根路径

        # ===== 容器初始化 =====
        self._kwargs = {}  # 内置参数字典
        self._tasks = []  # 总任务列表
        self._exceptions = {}  # 异常字典
        self._task_status = TaskStatus()  # 任务状态
        self.spider_config = {}  # 系统配置
        self.crawl_settings = {}  # 爬虫配置
        self.fail_tasks = set()  # 失败任务集合
        self.db = None  # 数据库
        self.mq = None  # RocketMQ
        self.cli_proxy = None  # cli proxy代理
        self.slack = None  # Slack消息

        # ===== 初始化流程 =====
        self._init_project_path()
        self._init_logger(*args)  # 日志初始化
        self._load_spider_config()  # 加载系统配置
        self._merge_configs()  # 合并配置并处理优先级
        self._init_tasks()  # 初始化任务列表
        self._load_crawl_settings()  # 加载爬虫配置
        self._init_upload_method()  # 初始化上传方法
        self._init_cli_proxy()  # 初始化cli proxy代理
        self._init_slack()  # 初始化slack

    def _init_project_path(self):
        """ 初始化项目路径
        将项目路径增加进系统路径
        :return:
        """
        project_path = os.path.join(self.base_path, '..')
        sys.path.append(project_path) if project_path not in sys.path else None

    def _init_logger(self, *args):
        """
        初始化日志系统
        """
        self.log = self._kwargs.get('log')

        if not self.log:
            super().__init__(
                *args,
                log_name=self.name,
                log_dir=self._kwargs.get(
                    'log_dir',
                    os.path.join(
                        self.base_path,
                        'logs',
                        self.name
                    )
                )
            )

    def _load_spider_config(self):
        """
        加载 spider_config.json 中的任务配置
        """
        config_path = os.path.join(
            self.base_path,
            "config",
            self.raw_kwargs.get('spider_config', 'spider_config.json')
        )

        self.spider_config = self._load_json(config_path)

    def _merge_configs(self):
        """
        合并配置，优先级：
            spider_config < raw_kwargs
            tasks < specify_tasks

        """
        # spider_config 中当前任务的配置
        self._kwargs.update(
            self.spider_config.get(self.name, {})
        )

        # 子类显式传入参数
        self._kwargs.update(self.raw_kwargs)

        # 特别任务
        self.specify_tasks = self._kwargs.get('specify_tasks', {})
        self._kwargs.update(self.specify_tasks)

        # 常用字段展开
        self.spider_mode = self._kwargs.get('env')

    def _init_tasks(self):
        """
        汇总所有类型任务
        """
        self._tasks = [
            task
            for task_type in ("tasks", "thread_tasks", "async_tasks")
            for task in self._kwargs.get(task_type, [])
        ]

    def _init_upload_method(self):
        """ 初始化数据上传方式
        根据spider_config.json中的相关配置参数调整。
        """
        if self._kwargs.get("db_settings", {}).get("enable"):
            db_settings = self._kwargs.get("db_settings", {}).copy()
            db_settings['log'] = self.log
            self.db = DatabaseConnect(**db_settings)
            self.db.commit = self._kwargs.get("commit", True)
            self.db.connect()
        if self._kwargs.get("mq_settings", {}).get("enable"):
            mq_settings = self._kwargs.get("mq_settings", {})
            kwargs = {
                "endpoints": mq_settings.get('endpoints').get(self.spider_mode),
                "auto_create": mq_settings.get("auto_create", False),
                "topic": mq_settings.get('topic'),
                "topics": None
                if self._kwargs.get('use_topic')
                else (
                    mq_settings.get('topic_format').format(i) for i in self.crawl_settings.keys()
                    if self._tasks and i in self._tasks
                ),
                "log": self.log,
            }
            self.mq = MQClient(**kwargs)
            if not self.mq.status:
                self.mq.startup_producer()

    def _init_cli_proxy(self):
        """
        初始化cli proxy代理
        :return:
        """
        cli_proxy_setting = {
            "name": self.name,
            "spider_mode": self.spider_mode,
            "log": self.log,
            **self._kwargs.get("cli_proxy", {})
        }  # cli_proxy代理配置
        self.cli_proxy = CliProxy(**cli_proxy_setting)  # 生成cli_proxy的类对象

    def _init_slack(self):
        """
        初始化slack
        :return:
        """
        self.slack_setting = self._kwargs.get("slack_setting", {})  # slack配置
        if self.slack_setting.get("enable", False):
            self.slack = SlackMessage(
                package_root_path=self.base_path,
                **self.slack_setting
            )

    def _load_crawl_settings(self):
        """
        加载爬虫运行配置
        """
        settings_path = os.path.join(
            self.base_path,
            'config',
            self._kwargs.get('crawl_settings', f'{self.name}.json')
        )

        self.crawl_settings = self._load_json(settings_path) or {}

    def _load_json(self, path: str) -> dict:
        """ 导入json文件数据

        :param path: 文件绝对路径
        :return: json文件数据内容
        """
        if not os.path.exists(path):
            self.log.error(f'[{self.name}] File [{path}] not exists')
            return {}
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _import_cls(
            self,
            cls_info: dict,
            func_name: str = 'function',
            func_path: str = 'function_path'
    ):
        """ 生成类对象或者手动导入并生成类对象
        首先判断是否类对象是否可用，否则根据func_path手动导入后生成。
        :param cls_info: 类信息字典，包含类的名称和类路径，最少包含以下两个信息
            {
                "function": ...,
                "function_path": ...
            }
        :param func_name: 类字典cls_info中类名称的指定键
        :param func_path: 类字典cls_info中类路径（相对于base_path）的指定键
        :return: 被引入的类对象
        """
        if not hasattr(self, "check_cls"):
            self.check_cls = {}
        if self.check_cls.get(cls_info[func_name]):
            return self.check_cls[cls_info[func_name]]
        try:
            cls = eval(cls_info[func_name])
            return cls
        finally:
            import_path = ".".join(cls_info[func_path].replace(".py", "").split("/"))
            if import_path.startswith("."):
                import_path = import_path[1:]
            module = importlib.import_module(import_path)
            cls = getattr(module, cls_info[func_name])
            self.check_cls[cls_info[func_name]] = cls
            return cls

    def _check_spider_status(self) -> None:
        """ 检查爬虫状态，
        可重写定义检查内容。
        :return:
        """
        [
            self.log.info(f"[spider:{self.name}] [{each}]: [{self._kwargs.get(each)}]")
            for each in self._kwargs.get("check_spider_status", ["env", "upload_to", "init_upload"])
        ]
        [
            self.log.info(f"[spider:{self.name}] [{each}]: [{len(self._kwargs[each])}] -> {set(self._kwargs[each])}")
            for each in ["tasks", "thread_tasks", "async_tasks"]
            if self._kwargs.get(each)
        ]
        use_proxy = set()
        [
            use_proxy.add(task)
            for task, task_settings in self.crawl_settings.items()
            if task_settings.get('proxy_setting') is not None and task in self._tasks
        ]
        if use_proxy:
            self.log.info(f"[spider:{self.name}] [proxy_usage]: {use_proxy}")

    def _check_connect_status(self) -> None:
        """ 检查链接状态
        根据情况关闭连接。
        :return:
        """
        if self.mq:
            self.mq.shutdown_producer()
        if self.db:
            self.db.close_connection()


class UploadMethod(InitParams):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _check_upload_items_and_upload_to(
            self,
            upload_obj: str,
            task: str,
            items: Any
    ) -> int:
        """ 检查待上传的项目并且上传
        上传的项目数据类型一共两种：
            - 一种是list、dict这类python关键字类型的，一般来说是使用MQ上传的

        :param upload_obj: 上传对象,大部分情况跟task相同，少部分不同，由任务脚本确定
        :param task: 任务对象，由框架配置确定
        :param items: 上传数据
        :return:
        """
        if items and isinstance(items, (list, dict)):
            len_of_items = len(items)
            self.log.info(f"[{upload_obj}] Process result[list|dict] have [{len_of_items}] items")
            if self.upload_items(
                    items,
                    self._kwargs.get("upload_to"),
                    **{
                        "upload_obj": upload_obj,
                        "task": task
                    },
            ):
                return len_of_items
        elif items and is_dataclass(items):
            len_of_items = len(items.data)
            self.log.info(f"[{upload_obj}] Process result[dataclass] have [{len_of_items}] items")
            if self.upload_items(
                    items.to_dict(),
                    self._kwargs.get("upload_to"),
                    **{
                        "upload_obj": upload_obj,
                        "task": task
                    },
            ):
                return len_of_items
        else:
            self.log.warning(f"[{upload_obj}] Process result type[{type(items)}] is not supported")
        return 0

    def upload_items(self, items: Any, upload_method: str | list = "db", **k) -> bool:
        """ 上传数据
        将数据以一定格式和指定方法上传，k作为额外参数，根据crawl_{project}.json的配置确定。
        :param items: [{"key":value}, ...]
        :param upload_method: 上传方式
        :param k: 上传的额外参数
        :return: True
        """
        upload_obj = k.get("upload_obj")
        upload_to_ = self.crawl_settings.get("upload_to", upload_method)
        _tag = True
        try:
            if "db" in upload_to_:  # noqa
                import pandas as pd
                db_settings = self._kwargs.get("db_settings", {})
                df = None
                table = None
                if isinstance(items, list):
                    df = pd.DataFrame(items)
                elif isinstance(items, pd.DataFrame):
                    df = items
                elif isinstance(items, dict):
                    df = pd.DataFrame([items])
                if db_settings.get("collection"):
                    table = db_settings["collection"]
                elif db_settings.get("collections"):
                    collections = db_settings["collections"]
                    for collection, match_list in collections:
                        if upload_obj in match_list:
                            table = collection
                            break
                if not table:
                    raise Exception(f"[{self.name}] collection not found")
                columns = ",".join(df.columns)
                values = ",".join(["%s"] * len(df.columns))
                updates = ",".join([f"{i}=VALUES({i})" for i in df.columns if i != 'unique_key'])
                sql = f"show columns from {table}"
                db_columns = [i['Field'] for i in self.db.execute_query(sql)]
                if not (set(df.columns) & set(db_columns)) == set(df.columns):
                    err_dict = {
                        "exception": set(df.columns) - set(db_columns),
                        "lack": set(db_columns) - set(df.columns),
                    }
                    self.log.error(f"df.columns has exceptional elements: {err_dict}")
                    raise Exception(err_dict)
                _sql = f"INSERT INTO `{table}` ({columns}) VALUES ({values}) ON DUPLICATE KEY UPDATE {updates}"
                try:
                    self.db.execute_insert_many(_sql, df.values.tolist())
                except Exception as e:
                    self.log.error(f"[{upload_obj}] {e}")
                    raise
                finally:
                    del df
            if "mq" in upload_to_:
                mq_settings = self._kwargs.get("mq_settings", {})
                topic = (
                        mq_settings.get("topics", {}).get(upload_obj)
                        or (
                            None
                            if self._kwargs.get("use_topic")
                            else mq_settings.get("topic_format").format(k.get("upload_obj"))
                        )
                )
                mq_kwargs = {
                    "topic": topic,
                    "tag": k.get("task"),
                }
                mq_kwargs.update(k)
                try:
                    self.mq.send_message(
                        items,
                        **mq_kwargs
                    )
                except Exception as e:
                    raise e
            if "api" in upload_to_:
                api_settings = self._kwargs.get("api_settings", {})
                endpoint = api_settings["endpoints"][self.spider_mode]
                upload_path = api_settings["upload_path"][k.get("upload_obj")]
                upload_url = urljoin(endpoint, upload_path)
                items_type = len(items) if (it := type(items)) == list else it
                try:
                    response = requests.post(upload_url, json=items)
                    if response.status_code == 200:
                        self.log.info(
                            f"[{upload_obj}] items[{upload_obj}:{items_type}] post to [{upload_url}] succeed.")
                    else:
                        raise Exception(f"{response.status_code}")
                except Exception as e:
                    self.log.warning(
                        f"[{upload_obj}] items[{upload_obj}:{items_type}] post to [{upload_url}] failed. [{e}]")
                    raise
        except Exception as e:
            e_ = f"[{self.name}] upload items failed: [{e}]"
            self.log.error(e_)
            self._exceptions[f"Upload:{int(time())}"] = e_
            _tag = False
        finally:
            del items
            return _tag


class Dispatcher(UploadMethod):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _format_proxy_params(self, spider_info: dict) -> dict:
        """ 代理的方法配置
        根据crawl_{project}.json的爬虫任务配置的proxy_setting确定需要哪种代理。
        :param spider_info: 传入的爬虫信息
        :return:
            {
                "fetch_proxies": ...,
                "proxy_setting": ...,
            }
        """
        if (proxy_setting := spider_info.get("proxy_setting")) is None or not proxy_setting.get("enable", False):
            return {
                "fetch_proxies": None,
                "proxy_setting": None,
            }
        else:
            proxy_setting = spider_info["proxy_setting"]
            proxy_setting.setdefault("spider_mode", self.spider_mode)
            agent = proxy_setting.get('agent')
            if agent == 'cli_proxy':
                return {
                    "fetch_proxies": self.cli_proxy.fetch_proxies,
                    "proxy_setting": proxy_setting
                }
            elif agent == 'qg_proxy':
                return {
                    "fetch_proxies": fetch_proxies_from_qg,
                    "proxy_setting": proxy_setting
                }
            elif agent == 'clash_proxy':
                return {
                    "fetch_proxies": fetch_proxies_from_clash,
                    "proxy_setting": proxy_setting
                }
            else:
                raise Exception(f"[{self.name}] agent [{agent}] not supported")

    def _format_func_params(self, task: str, task_settings: dict) -> dict:
        """ 格式化参数

        :param task: 任务标志
        :param task_settings: 任务配置
        :return:
        """
        # ====独立日志启用====
        log = Logger(
            log_name=task,
            log_dir=os.path.join(self.base_path, 'logs', self.name)
        ).log if task_settings.get("log_usage", False) else self.log
        # ====重复数据删除器====
        deduplicator = self._import_cls(
            cls_info={
                "function": "MilvusDeduplicator",
                "function_path": "utils/deduplicator"
            }
        )(
            log=log,
            **{  # 确定deduplicator_setting
                **self._kwargs.get("deduplicator_setting", {}),  # 框架配置
                **task_settings.get("deduplicator_setting", {})  # 二次覆盖
            }
        ) if task_settings.get("deduplicator_usage", False) else None
        # ====slack消息====
        slack_message = {
            "slack": self.slack,
            "Attachment": Attachment,
            "Field": Field,
        } if task_settings.get("slack_usage", False) else None
        # ====DB====
        db = DatabaseConnect(
            **task_settings.get("database_setting", {})
        ) if task_settings.get("db_usage", False) else None
        # ====func_params====
        func_params = {
            **task_settings,
            "env": self.spider_mode,
            "log": log,
            "deduplicator": deduplicator,
            "slack_message": slack_message,
            "db": db,
            **self._format_proxy_params(task_settings)
        }
        return func_params

    async def _run_spider_tasks(self, spider):
        """ 执行异步模式的爬虫任务
        启动异步模式下的爬虫任务，监听数据并上传。
        :param spider:
        :return:
        """
        # 启动爬虫并监听数据
        tag = True
        extra_params = spider.extra_params if hasattr(spider, "extra_params") else {}
        while tag:
            crawl_task = asyncio.create_task(spider.process())
            async for result in spider.upload_result():
                for upload_obj, items in result.items():
                    upload_num = self._check_upload_items_and_upload_to(upload_obj, spider.name, items)
                    self._task_status.ProcessAsync[spider.name] += upload_num
            await crawl_task  # 等待爬虫任务完成
            tag = extra_params.get('continued_enable', False)
            if hasattr(spider, "exceptions"):
                self._exceptions.update({f"ProcessAsync:{k}": v for k, v in spider.exceptions.items()})
            if tag:
                self.send_task_status_to_slack()
                self._task_status = TaskStatus()
                self._exceptions.clear()
                spider.re_execute()
                await asyncio.sleep(extra_params.get("wait_time", 0))

    async def process_async(self) -> bool:
        """ 多线程运行任务
        多线程异步执行async_tasks的所有任务，抓取配置根据crawl_{project}.json来确定。
        适合多线程下多次获取数据并返回的爬虫脚本。
        模板爬虫文件看: /spiders/_async_template.py
        每一个 task：
        └── 一个独立线程
              └── 一个独立 event loop
                    ├── spider.process()  # 任务执行
                    └── spider.upload_result()  # 上传结果
        :return: True
        """
        threads = {}
        tasks = self._kwargs.get("async_tasks")
        for task in tasks:
            if self.crawl_settings.get(task) is None:
                e_ = f"[spider:{self.name}] async [{task}] does not exits in [{self._kwargs.get('crawl_settings')}]"
                self.log.warning(e_)
                self._exceptions[f"ProcessAsync:{int(time())}"] = e_
                continue
            task_settings = self.crawl_settings[task]
            try:
                func_params = self._format_func_params(task, task_settings)
                spider = self._import_cls(task_settings)(**func_params)
                loop = asyncio.new_event_loop()  # 为每个线程创建一个新的事件循环
                if self.system == "Linux":
                    # linux环境下，利用信号机制，合理中断被执行的多线程异步爬虫任务 -> kill -2 [pid]
                    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(spider.stop_process_async()))
                asyncio.set_event_loop(loop)  # 设置当前线程的事件循环
                thread = threading.Thread(
                    target=lambda s: loop.run_until_complete(self._run_spider_tasks(s)),
                    args=(spider,),
                    name=task
                )
                threads[thread] = spider
                thread.start()
                self._task_status.ProcessAsync[task] = 0
                self.log.info(f"[{task}] add to async threads.")
            except Exception as e:
                e_ = f"[{task}] add to async threads error: {e}"
                self.log.warning(e_)
                self._exceptions[f"ProcessAsync:{int(time())}"] = e_
        # 等待所有线程执行完
        for thread in threads:
            task = thread.name
            try:
                thread.join()
            except Exception as e:
                self.log.error(f"[{task}] async threads: {e}")
                self._task_status.ProcessAsync[task] = e
            finally:
                if hasattr(threads[thread], "exceptions"):
                    function = threads[thread]
                    self._exceptions.update({f"ProcessAsync:{k}": v for k, v in function.exceptions.items()})
        return True

    def process_thread(self) -> bool:
        """ 多线程运行任务
        多线程执行thread_tasks的所有任务，抓取配置根据crawl_{project}.json来确定。
        适合多线程下一次性获取数据并返回的爬虫脚本。
        :return: True
        """
        threads = {}
        thread_settings = self._kwargs.get("thread_settings", {})
        tasks = self._kwargs.get("thread_tasks")
        with ThreadPoolExecutor(max_workers=thread_settings.get("max_workers", 5)) as executor:
            for task in tasks:
                if self.crawl_settings.get(task) is None:
                    e_ = " ".join([
                        f"[spider:{self.name}]",
                        f"thread [{task}]",
                        f"does not exits in",
                        f"[{self._kwargs.get('crawl_settings')}]",
                    ])
                    self.log.warning(e_)
                    self._exceptions[f"ProcessThread:{int(time())}"] = e_
                    continue
                task_settings = self.crawl_settings[task]
                try:
                    func_params = self._format_func_params(task, task_settings)
                    function = self._import_cls(task_settings)(**func_params)
                    thread = executor.submit(
                        function.process
                    )
                    thread.meta = {"task": task}
                    threads[thread] = function
                    self._task_status.ProcessThread[task] = 0
                    self.log.info(f"[{task}] add to threads.")
                except Exception as e:
                    e_ = f"[{task}] add to threads error: {e}"
                    self.log.warning(e_)
                    self._exceptions[f"ProcessThread:{int(time())}"] = e_
            for future in as_completed(threads):
                task = future.meta["task"]
                try:
                    result = future.result()
                    for each in result:
                        for upload_obj, items in each.items():
                            upload_num = self._check_upload_items_and_upload_to(upload_obj, task, items)
                            self._task_status.ProcessThread[task] = upload_num
                except Exception as e:
                    self.fail_tasks.add(task)
                    self.log.error(f"[{task}] error: {e}")
                    self._task_status.ProcessThread[task] = e
                finally:
                    if hasattr(threads[future], "exceptions"):
                        function = threads[future]
                        self._exceptions.update({f"ProcessTread:{k}": v for k, v in function.exceptions.items()})
                    del future
        return True

    def process(self) -> bool:
        """ 单线程同步运行任务
        顺序执行tasks的所有任务，抓取配置根据crawl_{project}.json来确定。
        :return: True
        """
        tasks = self._kwargs.get("tasks")
        for task in tasks:
            if self.crawl_settings.get(task) is None:
                e_ = f"[spider:{self.name}] [{task}] does not exits in [{self._kwargs.get('crawl_settings')}]"
                self.log.warning(e_)
                self._exceptions[f"Process:{int(time())}"] = e_
                continue
            task_settings = self.crawl_settings[task]
            function = None
            try:
                func_params = self._format_func_params(task, task_settings)
                function = self._import_cls(task_settings)(**func_params)
                result = function.process()
                self._task_status.Process[task] = 0
                for each in result:
                    for upload_obj, items in each.items():
                        upload_num = self._check_upload_items_and_upload_to(upload_obj, task, items)
                        self._task_status.Process[task] = upload_num
            except Exception as e:
                self._task_status.Process[task] = e
                self.fail_tasks.add(task)
                self.log.error(f"[{task}] error: {e}")
            finally:
                if hasattr(function, "exceptions"):
                    self._exceptions.update({f"Process:{k}": v for k, v in function.exceptions.items()})
                del function
        return True

    def send_task_status_to_slack(self):
        """ 发送任务执行状态到Slack

        :return:
        """
        if not self.slack_setting.get('enable', False):
            return
        task_results = self._task_status.to_result()
        if any(task_results):
            color = "danger"
        elif self._exceptions and len(self._exceptions) > self.slack_setting.get("exception_limit", 0):
            color = "warning"
        else:
            color = "good"
        level_dict = {
            "good": 0,
            "warning": 1,
            "danger": 2,
        }
        filter_level = self.slack_setting.get("filter_level", "good")
        if level_dict[color] < level_dict[filter_level]:
            return False
        _succeed = task_results.count(False)
        _fail = task_results.count(True)
        _count = len(self._tasks)
        exec_info = "， ".join(
            [
                f"预计：{_count}",
                f"成功：{_succeed}",
                f"失败：{_fail}",
                f"异常：{len(self._exceptions)}",
            ]
        )
        exec_details = [
            f"任务 [{k}] 执行结果为: {v}"
            for task_status in [
                self._task_status.Process,
                self._task_status.ProcessThread,
                self._task_status.ProcessAsync,
            ]
            for k, v in task_status.items()
        ]
        exception_ = [
            f"[{k}] {v}"
            for k, v in self._exceptions.items()
        ]
        fields = [
            Field(title="执行状态", value=f"在环境 [{self.spider_mode}] 执行完成", short=True),
            Field(title="执行信息", value=exec_info, short=True),
            Field(title="任务详情", value="\n".join(exec_details), short=False),
            # 只显示前五十条异常信息
            Field(title="异常情况", value="\n".join(exception_[:50]), short=False) if self._exceptions else None
        ]
        _text = f"[{_count}] 个任务" if _count > 5 else "，".join(self._tasks)
        attachment = Attachment(
            title=f"[{self.name}] 执行报告",
            text=f"脚本 [{self.name}] 预期执行 {_text}",
            color=color,
            author_name="@weist"
        )
        self.slack.send_message(attachment=attachment, fields=fields)
        self.log.info(f"[{self.name}] Task details send to slack")

    def crawl(self):
        """ 抓取入口函数
        在此配置框架执行流程
        :return:
        """
        title_size = 100
        date_format = "%Y-%m-%d %H:%M:%S"
        today_ = datetime.today
        self.log.info(f"{f' [Crawl start at {(start_time := today_().strftime(date_format))}] ':~^{title_size}}")
        try:
            self._check_spider_status()
            if self._kwargs.get("tasks"):
                self.process()
            if self._kwargs.get("thread_tasks"):
                self.process_thread()
            if self._kwargs.get("async_tasks"):
                asyncio.run(self.process_async())
            if self.fail_tasks:
                self.log.warning(f"Tasks execute failed: {self.fail_tasks}")
        except Exception as e:
            self.log.error(f"[{self.name}] crawl error: {e}")
            self._exceptions["Crawl"] = e
        finally:
            self._check_connect_status()
            self.send_task_status_to_slack()
            self.log.info(f"{f' [Crawl finish at {(finish_time := today_().strftime(date_format))}] ':~^{title_size}}")
            self.close_log()
        subprocess_output = {
            "project": self.name,
            "tasks": self._tasks,
            "start_time": start_time,
            "finish_time": finish_time,
            "status": "done"
        }
        print(json.dumps(subprocess_output))  # subprocess标准化输出捕获

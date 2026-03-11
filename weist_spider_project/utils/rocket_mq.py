# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/10/18 10:01
# @File:        rocket_mq.py
# @Software:    PyCharm
# @Description: 上传数据至RocketMQ的代码。
import asyncio
import json
import logging
from typing import Any

import requests
from rocketmq import ClientConfiguration, Credentials, Producer, Message
from rocketmq.v5.log.log_config import logger

logger.level = logging.CRITICAL
for handler in logger.handlers:
    logger.removeHandler(handler)


def handle_send_result(result_future):
    try:
        print(result_future)
        res = result_future.result()
        print(f"send message success, {res}")
    except Exception as exception:
        print(f"send message failed, raise exception: {exception}")


class MQClient:
    log = None
    status = False
    missing_topics = set()

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.endpoints = kwargs.get('endpoints')
        self.topic = kwargs.get('topic')
        self.topics = kwargs.get("topics")
        self.auto_create = kwargs.get("auto_create", False)
        self.ak = kwargs.get('ak')
        self.sk = kwargs.get('sk')
        self.producer = None
        self.log = kwargs.get('log')
        self.topic_in_mq = []
        if not self.producer:
            self._create_producer()
        self.topic_exists = set()
        self.queue = asyncio.Queue(16)

    def _print(self, msg: str, level: str = "info"):
        if self.log:
            level_dict = {
                "info": self.log.info,
                "error": self.log.error,
                "warn": self.log.warning,
            }
            level_dict[level](msg)
        else:
            print(msg)

    def _check_credentials(self):
        if self.ak == self.sk is None:
            return Credentials()
        else:
            return Credentials(ak=self.ak, sk=self.sk)

    def _create_producer(self):
        self._check_topics_exist()
        credentials = self._check_credentials()
        config = ClientConfiguration(endpoints=self.endpoints, credentials=credentials)
        if self.topic is None:
            raise Exception("topic is None")
        else:
            self.producer = Producer(config, self.topics or (self.topic,))
            self.producer_name = f"{self.producer.__str__()}"

    def _check_topics_exist(self):
        if self.auto_create:
            self._query_topics()
            for topic in self.topics or (self.topic,):
                if topic not in self.topic_in_mq:
                    self._create_topic(topic)

    def _check_topic_exist(self, topic=None):
        if self.auto_create:
            self._query_topics() if not self.topic_in_mq else None
            if topic not in self.topic_in_mq:
                self._create_topic(topic)

    def startup_producer(self):
        if self.producer is None:
            raise Exception("producer is None")

        self.producer.startup()
        self._print("Producer startup")
        self.status = self.producer.is_running

    def shutdown_producer(self):
        if self.producer is None:
            raise Exception("producer is None")
        self.producer.shutdown()
        self._print("Producer shutdown")
        if self.missing_topics:
            self._print(f"[RocketMQ] Failed topics({self.missing_topics})", "warn")

    def _check_message(self, msg: Any):
        if isinstance(msg, str):
            return msg.encode('utf-8')
        elif isinstance(msg, (list, dict, tuple)):
            return json.dumps(msg).encode('utf-8')
        elif isinstance(msg, bytes):
            return msg
        else:
            raise Exception("msg type error")

    def _create_message(self, data: Any, tag: str, keys: str, topic: str = None):
        msg = Message()
        msg.body = self._check_message(data)
        msg.topic = topic or self.topic
        msg.tag = tag
        msg.keys = keys
        msg.add_property("send", "sync")
        return msg

    def _send_message(
            self,
            msg: Any,
            **k
    ):
        topic = k.get("topic", self.topic)
        tag: str = k.get("tag", "weist_tag")
        keys: str = k.get("keys", "weist_keys")
        task_name = k.get("task", "")
        self._check_topic_exist(topic)
        if self.producer is None:
            raise Exception("producer is None")
        msg = self._create_message(msg, tag, keys, topic)
        # res = self.producer.send(msg)
        res = self.producer.send_async(msg).result()
        self._print(f"[{task_name}] Message({res}) send to Topic({topic or self.topic}) success.")

    def send_message(self, msg: Any, **k):
        attempt = k.get("attempt", 0)
        if attempt > 3:
            self._print(
                " ".join(
                    [
                        f"[{k.get('task', '')}]",
                        f"RocketMQ Topic({k.get('topic') or self.topic})",
                        f"Attempts({attempt})",
                        "all resend attempt failed"
                    ]
                ),
                "error"
            )
            return
        try:
            self._send_message(msg, **k)
        except Exception as e:
            self._print(
                " ".join(
                    [
                        f"[{k.get('task', '')}]",
                        f"RocketMQ Topic({k.get('topic') or self.topic})",
                        f"Attempts({attempt})",
                        f"exception({e})"
                    ]
                ),
                "warn"
            )
            self.missing_topics.add(k.get('topic') or self.topic)
            self.send_message(msg, attempt=attempt + 1)

    def _query_topics(self):
        endpoints = self.endpoints.replace("9874", "19876")
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Referer": f"http://{endpoints}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
        }
        cookies = {

        }
        url = f"http://{endpoints}/topic/list.query"
        response = requests.get(url, headers=headers, cookies=cookies, verify=False)
        if response.status_code == 200:
            self.topic_in_mq = response.json().get("data").get("topicList")

    def _create_topic(self, topic: str):
        endpoints = self.endpoints.replace("9874", "19876")
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": f"http://{endpoints}",
            "Referer": f"http://{endpoints}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
        }
        url = f"http://{endpoints}/topic/createOrUpdate.do"
        data = {
            "writeQueueNums": 16,
            "readQueueNums": 16,
            "perm": 6,
            "order": False,
            "topicName": topic,
            "brokerNameList": [
                "broker-a"
            ],
            "clusterNameList": [
                "DefaultCluster"
            ]
        }
        response = requests.post(url, headers=headers, json=data, verify=False)
        if response.status_code == 200:
            self._print(f"[RocketMQ] Create Topic({topic}) success at [{endpoints}]")
            self._query_topics()
        else:
            self._print(f"[RocketMQ] Create Topic({topic}) failed at [{endpoints}]")

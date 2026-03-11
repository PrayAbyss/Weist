# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/10/1 10:01
# @File:        cliproxy.py
# @Software:    PyCharm
# @Description: cliproxy的代理生成代码。
import json
import os
import random
import string

import requests


class CliProxy(object):

    def __init__(self, *args, **kwargs):
        self._kwargs = {}
        self._kwargs.update(kwargs)
        self.log = self._kwargs.get('log')
        self.name = self._kwargs.get('name')
        self.spider_mode = self._kwargs.get('spider_mode')
        self.proxy_tag = {}
        self.proxies = {}

    def _print(self, msg, level='info'):
        if self.log is None:
            print(msg)
        else:
            level_dict = {
                "info": self.log.info,
                "debug": self.log.debug,
                "warn": self.log.warning,
                "error": self.log.error,
            }
            level_dict[level](msg)

    def _load(self, path):
        if not os.path.exists(path):
            self._print(f"[{self.name}]: file [{path}] not exist")
            return None
        with open(path, 'r') as f:
            return json.load(f)

    def _create_proxy(self, **k):
        check = lambda key: k.get(key) or self._kwargs.get(key)

        username = check("username")
        password = check("password")
        host = check("host")
        port = check("port")
        concat_list = [username]
        if check("regions"):
            regions = check("regions")
            region = f"region-{'_'.join(regions)}"
            concat_list.append(region)
            if len(regions) == 1 and check("states"):
                states = check("states")
                state = f"st-{'_'.join(states)}"
                concat_list.append(state)
                if len(states) == 1 and check("cities"):
                    cities = check("cities")
                    city = f"city-{'_'.join(cities)}"
                    concat_list.append(city)
        else:
            region = "region-Rand"
            concat_list.append(region)
        if k.get("flash_time"):
            sid = "".join(random.choices(string.ascii_letters, k=10))
            flash_time = int(k["flash_time"])
            session_type = f"sid-{sid}-t-{flash_time}"
            concat_list.append(session_type)
        proxy = f"http://{'-'.join(concat_list)}:{password}@{host}:{port}"
        proxies = {
            "http": proxy,
            "https": proxy,
        }
        return proxies

    def _check_proxy(self, proxies):
        check_url = self._kwargs.get("check_url", "https://mayips.com")
        response = requests.get(url=check_url, proxies=proxies)
        if response.status_code == 200:
            return proxies
        else:
            raise Exception(f"[{self.name}] | check [{proxies['http']}] failed | {response.status_code}")

    def fetch_proxies(
            self,
            check_proxy: bool = False,
            **k
    ):
        if self.spider_mode == "local":
            proxies = {
                "http": "http://127.0.0.1:7890",
                "https": "http://127.0.0.1:7890",
            }
        else:
            proxies = self._create_proxy(**k)
        if check_proxy:
            return self._check_proxy(proxies)
        return proxies


if __name__ == '__main__':
    username = "*********"
    password = "*********"
    kwargs = {
        "username": username,
        "password": password,
        "host": "**.***.io",
        "port": 3010,
        "flash_time": 1,
        "regions": ["US"],
        "states": ["Arizona"],
        "cities": ["Phoenix"],
    }
    cp = CliProxy(**{
        "name": "test",
        "spider_mode": "test",
        "username": username,
        "password": password,
        "host": "**.***.io",
        "port": 3010,
        # "flash_time": 1,
        "regions": ["HK"],
        # "states": ["Arizona"],
        # "cities": ["Phoenix"],
        "flash_time": 120,

    })
    p = cp.fetch_proxies(
        check_proxy=False,
        **{

            "flash_time": 120,
            "regions": ["US"],
        }
    )
    print(p)

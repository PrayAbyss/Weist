# -*- coding: utf-8 -*-
# @Author:      weist
# @Date:        2025/8/30 10:01
# @File:        tools.py
# @Software:    PyCharm
# @Description: 工具方法。
import io
import os
import zipfile

import requests


class SpiderMode:
    Local = "local"
    Test = "test"
    Production = "prod"


def httpx_request(
        url,
        extract: list = None,
        extract_type: str = "json",
        attempts: int = 3,
        method: str = "get",
        check_status_code: bool = True,
        base_delay: int | float = 0,
        check_text: bool = False,
        **rk
) -> dict | str | list:
    """ httpx 定制

    :param url: 网址
    :param extract: 提取路径列表， 当提取类型为json时生效
    :param extract_type: 提取类型
    :param attempts: 尝试次数
    :param method: 请求类型
    :param check_status_code: 检查响应状态码，如果直接获取结果可以关闭
    :param base_delay: 退避算法延迟基数
    :param rk: 请求参数
    :return: 返回提取内容
    :raise: 所有尝试失败后，自动抛出异常
    """
    from httpx import request as hr
    from time import sleep
    exception = f"[HTTPX_REQUEST] method({method}) url({url}) failed:"
    exception_count = {}
    for attempt in range(attempts):
        try:
            response = hr(method, url, **rk)
            print(response.text.replace("\n", "")) if check_text else None
            response.raise_for_status() if check_status_code else None
            if extract_type == "json":
                return (func := lambda i, ex: func(i[ex.pop(0)], ex) if ex else i)(response.json(), extract)
            elif extract_type == "text":
                return response.text
            else:
                exception += f"exception([{extract_type}] not support)"
                break
        except KeyError as e:
            exception += f" extract({extract}) exception key({e})" if str(e) not in exception else ""
            break
        except IndexError as e:
            exception += f" extract({extract}) exception index({e})" if str(e) not in exception else ""
            break
        except Exception as e:
            e_ = str(e).replace("\n", "").strip()[:100]
            if exception_count.get(e_) is None:
                exception_count[e_] = 1
            else:
                exception_count[e_] += 1
            # exception += f" exception({e_})" if e_ not in exception else ""
        delay = base_delay ** (attempt + 1)
        sleep(delay)
    exception += ", ".join([f"{k} -> {v}" for k, v in exception_count.items()])
    raise Exception(exception)


def curl_request(
        url,
        extract: list = None,
        extract_type: str = "json",
        attempts: int = 3,
        method: str = "get",
        check_status_code: bool = True,
        base_delay: int | float = 0,
        **rk
) -> dict | str | list:
    """ curl 定制

    :param url: 网址
    :param extract: 提取路径列表， 当提取类型为json时生效
    :param extract_type: 提取类型
    :param attempts: 尝试次数
    :param method: 请求类型
    :param check_status_code: 检查响应状态码，如果直接获取结果可以关闭
    :param base_delay: 退避算法延迟基数
    :param rk: 请求参数
    :return: 返回提取内容
    :raise: 所有尝试失败后，自动抛出异常
    """
    from curl_cffi import request as cr
    from time import sleep
    exception = f"[CURL_REQUEST] method({method}) url({url}) failed:"
    for attempt in range(attempts):
        try:
            response = cr(method, url, **rk)  # noqa
            response.raise_for_status() if check_status_code else None
            if extract_type == "json":
                return (func := lambda i, ex: func(i[ex.pop(0)], ex) if ex else i)(response.json(), extract)
            elif extract_type == "text":
                return response.text
            else:
                exception += f"exception([{extract_type}] not support)"
                break
        except KeyError as e:
            exception += f" extract({extract}) exception({e})" if str(e) not in exception else ""
            break
        except IndexError as e:
            exception += f" extract({extract}) exception({e})" if str(e) not in exception else ""
            break
        except Exception as e:
            e_ = str(e).replace("\n", "").strip()[:100]
            exception += f" exception({e_})" if e_ not in exception else ""
        delay = base_delay ** (attempt + 1)
        sleep(delay)
    raise Exception(exception)


def fetch_proxies_from_qg(
        spider_mode: str = SpiderMode.Local,
        source: int = 0,
        check: bool = True,
        attempts: int = 11,
        update: dict = None,
        **k: dict
) -> dict:
    return fetch_proxies_from_clash(**k)


def fetch_proxies_from_clash(**k):
    return {
        "http": "http://127.0.0.1:7890",
        "https": "http://127.0.0.1:7890",
    }


def json_action(path: str, action="load", default=None, data=None) -> list | dict | str:
    import json
    import os
    if action == "load":
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data_ = json.load(f)
            return data_
        else:
            return default
    elif action == "save":
        if isinstance(data, (dict, list, tuple)):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return f"[JSON ACTION] Path({path}) Action({action}) Data({str(data)[:50]}) success"
        else:
            raise Exception(f"[JSON ACTION] Path({path}) Action({action}) save fail")


def download_and_extract_zip(
        url: str,
        dir_name: str = None,
        base_dir: str = None,
        check_files: list = None,
        proxies: dict = None
):
    """下载并解压zip文件

    :param url: 文件地址
    :param dir_name: 指定文件夹
    :param base_dir: 基础文件夹绝对路径
    :param check_files: 检查文件是否存在
    :param proxies: 代理
    :return:
    """
    base_path = base_dir or os.path.dirname(os.path.abspath(__file__))
    dir_path = os.path.join(base_path, dir_name or "zip_dir")
    if any([os.path.exists(os.path.join(dir_path, file)) for file in check_files]):
        print("file already downloaded")
        return dir_path
    try:
        response = requests.get(url, proxies=proxies)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(dir_path)
        return dir_path
    except Exception as e:
        raise Exception(f"zip extracted | [{url}] failed | {e}")


def parse_tags(items, nt=None, cnt=None, pm=None):
    """
    用来解析字典格式的数据，pm的key值要随实际情况调整
    :param items: 解析的数据列表
    :param pm: parse_methods 解析方法
    :param nt: node_type 标签类型判断字段
    :param cnt: child_node_type 子节点字段
    :return:
    """
    if not items or not isinstance(items, list):
        return ""
    if pm is None:
        pm = {
            "text": lambda n: n.get("value", ""),
            "paragraph": lambda n: f'<p>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</p>',
            "link": lambda n: f'<span>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</span>',
            "emphasis": lambda n: f'<em>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</em>',
            "strong": lambda n: f'<strong>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</strong>',
            "unordered-list": lambda n: f'<ul>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</ul>',
            "ordered-list": lambda n: f'<ol>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</ol>',
            "list-item": lambda n: f'<li>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</li>',
            "table": lambda n: f'<table><tbody>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</tbody></table>',
            "table-row": lambda n: f'<tr>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</tr>',
            "table-cell": lambda n: f'<td>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</td>',
            "blockquote": lambda n: f'<blockquote>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</blockquote>',
            "hr": lambda n: '<hr>',
            "break": lambda n: '<br>',
            **{
                f"heading-{l}": (lambda n, level=l: f'<h{level}>{parse_tags(n.get(cnt, []), nt, cnt, pm)}</h{level}>')
                for l in range(1, 7)
            }
        }
    return "".join([pm.get(i[nt], lambda *n: print(i) or "")(i) for i in items])

# -*- coding: utf-8 -*-
# @Author:      weist
# @Date:        2025/8/30 10:01
# @File:        tools.py
# @Software:    PyCharm
# @Description: 工具方法。
import io
import os
import zipfile
from asyncio import Semaphore, sleep as asyncio_sleep
from time import sleep

import requests
from curl_cffi import request as cr
from httpx import request as hr, stream as hs, AsyncClient


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
        check_text: bool = False,
        base_delay: int | float = 0,
        **rk
) -> dict | str | list:
    """ httpx 定制

    :param url: 网址
    :param extract: 提取路径列表， 当提取类型为json时生效
    :param extract_type: 提取类型
    :param attempts: 尝试次数
    :param method: 请求类型
    :param check_status_code: 检查响应状态码，如果直接获取结果可以关闭
    :param check_text: 查看响应文本
    :param base_delay: 退避算法延迟基数
    :param rk: 请求参数
    :return: 返回提取内容
    :raise: 所有尝试失败后，自动抛出异常
    """

    exception = f"[HTTPX_REQUEST] Method({method}) Url({url[:100]}) failed: "
    exception_count = {}
    last_lst = []
    for attempt in range(attempts):
        try:
            response = hr(method, url, **rk)
            print(response.text.replace("\n", "")) if check_text else None
            response.raise_for_status() if check_status_code else None
            if extract_type == "json":
                return (
                    func := lambda i, ex, ll: func(i[ll.append(ki := ex.pop(0)) or ki], ex, ll) if ex else i
                )(response.json(), extract, last_lst)
            elif extract_type == "text":
                return response.text
            else:
                exception += f"Exception([{extract_type}] not support)"
                break
        except (KeyError, IndexError) as e:
            exception += f"ExtractList({extract}) Current Key/Index({last_lst[-1]}) Exception({e})"
            break
        except Exception as e:
            e_ = str(e).replace("\n", "").strip()[:100]
            if exception_count.get(e_) is None:
                exception_count[e_] = 1
            else:
                exception_count[e_] += 1
        delay = base_delay ** (attempt + 1)
        sleep(delay)
    exception += ", ".join([f"Exception({k} -> {v})" for k, v in exception_count.items()])
    raise Exception(exception)


async def httpx_client(
        client: AsyncClient,
        sem: Semaphore,
        extract: list = None,
        extract_type: str = "json",
        attempts: int = 3,
        check_status_code: bool = True,
        check_text: bool = False,
        base_delay: int | float = 0,
        **rk
) -> dict:
    """ 异步请求
    响应返回rk是为了标识是哪个请求，以免并发过程丢失失败请求。
    :param client: AsyncClient，httpx的异步客户端
    :param sem: 限定并发
    :param extract: 提取列表
    :param extract_type: 提取类型
    :param attempts: 尝试此时
    :param check_status_code: 检查响应码
    :param check_text: 检查响应文本
    :param base_delay: 基础延迟
    :param rk: 请求参数
    :return: rk,响应结果在rk的"_result"字段中
    """
    exception = f"[HTTPX_CLIENT] Method({rk.get('method')}) Url({rk.get('url', '')[:100]}) failed: "
    exception_count = {}
    last_lst = []
    async with sem:
        for attempt in range(attempts):
            try:
                response = await client.request(**rk)
                print(response.text.replace("\n", "")) if check_text else None
                response.raise_for_status() if check_status_code else None
                if extract_type == "json":
                    return rk.setdefault(
                        "_result",
                        (
                            func := lambda i, ex, ll: func(i[ll.append(ki := ex.pop(0)) or ki], ex, ll) if ex else i
                        )(response.json(), extract, last_lst)
                    )
                elif extract_type == "text":
                    return rk.setdefault("_result", response.text)
                else:
                    exception += f"Exception([{extract_type}] not support)"
                    break
            except (KeyError, IndexError) as e:
                exception += f"ExtractList({extract}) Current Key/Index({last_lst[-1]}) Exception({e})"
                break
            except Exception as e:
                e_ = str(e).replace("\n", "").strip()[:100]
                if exception_count.get(e_) is None:
                    exception_count[e_] = 1
                else:
                    exception_count[e_] += 1
            delay = base_delay ** (attempt + 1)
            await asyncio_sleep(delay)
        exception += ", ".join([f"Exception({k} -> {v})" for k, v in exception_count.items()])
        raise Exception(exception)


def httpx_stream(url: str, file_path: str, **rk):
    headers = {}
    mode = "wb"
    # 如果文件存在，尝试断点续传
    if os.path.exists(file_path):
        os.remove(file_path)
    with hs("GET", url, headers=headers, timeout=None, **rk) as r:
        r.raise_for_status()
        with open(file_path, mode) as f:
            for chunk in r.iter_bytes(81920):
                if chunk:
                    f.write(chunk)
    return file_path


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

    exception = f"[CURL_REQUEST] Method({method}) Url({url[:100]}) failed: "
    exception_count = {}
    last_lst = []
    for attempt in range(attempts):
        try:
            response = cr(method, url, **rk)  # noqa
            response.raise_for_status() if check_status_code else None
            if extract_type == "json":
                return (
                    func := lambda i, ex, ll: func(i[ll.append(ki := ex.pop(0)) or ki], ex, ll) if ex else i
                )(response.json(), extract, last_lst)
            elif extract_type == "text":
                return response.text
            else:
                exception += f"Exception([{extract_type}] not support)"
                break
        except (KeyError, IndexError) as e:
            exception += f" Extract({extract}) Current Key/Index({last_lst[-1]}) ({e})" if str(
                e) not in exception else ""
            break
        except Exception as e:
            e_ = str(e).replace("\n", "").strip()[:100]
            if exception_count.get(e_) is None:
                exception_count[e_] = 1
            else:
                exception_count[e_] += 1
        delay = base_delay ** (attempt + 1)
        sleep(delay)
    exception += ", ".join([f"Exception({k} -> {v})" for k, v in exception_count.items()])
    raise Exception(exception)


def fetch_proxies_from_qg(
        spider_mode: str = "local",
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

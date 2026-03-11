# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/-/- 00:00
# @File:        _async_template.py
# @Software:    PyCharm
# @Description: 模板文件
import asyncio
import json
import os

from httpx import AsyncClient

from weist_spider_project.spiders.liquidation.utlils.models import Liquidation
from weist_spider_project.spiders.liquidation.utlils.tools import get_trading_pair, decrypt_from_app
from weist_spider_project.utils.spider import AsyncSpider, async_func_test, auto_execute_method

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class LiqHeatMapTraPairModel2(AsyncSpider):
    name = "liq_heat_map_tra_pair_model_2"
    script_type = "async"
    log = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ====自定义====
        self.trading_pairs = []
        self.params_batch = []
        self.domin = self.extra_params.get('domin')
        self.url = f"{self.domin}/api/index/v5/liqHeatMap"
        self.headers = {
            "User-Agent": "vivo/V2344A",
            "Accept-Encoding": "gzip",
            "obe": "",
            "language": "en",
            "process": "true"
        }
        self.sem = asyncio.Semaphore(self.extra_params.get("sem", 30))
        self.time_interval_params = {
            "12h": {
                "interval": "5",
                "limit": "144",
            },
            "1d": {
                "interval": "5",
                "limit": "288",
            },
            "2d": {
                "interval": "15",
                "limit": "192",
            },
            "3d": {
                "interval": "15",
                "limit": "288",
            },
            "1w": {
                "interval": "30",
                "limit": "336",
            },
            "2w": {
                "interval": "30",
                "limit": "672",
            },
            "1m": {
                "interval": "h2",
                "limit": "372",
            },
            "3m": {
                "interval": "h6",
                "limit": "360",
            },
            "6m": {
                "interval": "h12",
                "limit": "360",
            },
            "1y": {
                "interval": "h24",
                "limit": "360",
            }
        }
        self.time_interval_reverse = {"-".join(v.values()): k for k, v in self.time_interval_params.items()}

    # ======================脚本代码=========================
    async def fetch_all_exchange_trading_pairs(self):
        exchanges = self.extra_params.get("exchanges", [])
        for exchange in exchanges:
            exchange_tra_pairs = get_trading_pair(exchange)
            if tra_pairs := self.extra_params.get("tra_pairs"):
                for tra_pair in tra_pairs:
                    for etp in exchange_tra_pairs:
                        if tra_pair in etp:
                            self.trading_pairs.append(etp)
                            break
                    else:
                        self._print(f"[{self.name}] tra_pair({tra_pair}) compare fail", "error")
            else:
                self.trading_pairs.extend(exchange_tra_pairs)

    async def init_params_batch(self):
        time_interval = (
                self.extra_params.get("time_interval")
                or ['12h', '1d', '2d', '3d', '1w', '2w', '1m', '3m', '6m', '1y']
        )
        for trading_pair in self.trading_pairs:
            for interval in time_interval:
                params = {
                    "merge": "true",
                    "symbol": trading_pair,
                    "from": "android",
                    **self.time_interval_params.get(interval, {})
                }
                self.params_batch.append(params)

    async def fetch(
            self,
            client: AsyncClient,
            extract: list = None,
            extract_type: str = "json",
            attempts: int = 3,
            check_status_code: bool = True,
            base_delay: int | float = 0,
            **rk
    ):
        exception = f"[HTTPX_REQUEST] method({rk.get('method')}) url({rk.get('url')}) failed: "
        async with self.sem:
            for attempt in range(attempts):
                try:
                    response = await client.request(**rk)
                    response.raise_for_status() if check_status_code else None
                    if extract_type == "json":
                        result = (func := lambda i, ex: func(i[ex.pop(0)], ex) if ex else i)(response.json(), extract)
                    elif extract_type == "text":
                        result = response.text
                    elif extract_type == "response":
                        result = response  # noqa
                    else:
                        raise Exception(f"extract_type[{extract_type}] not support")
                    rk['result'] = result
                    return rk
                except KeyError as e:
                    exception += f" extract({extract}) exception key({e})" if str(e) not in exception else ""
                    break
                except IndexError as e:
                    exception += f" extract({extract}) exception index({e})" if str(e) not in exception else ""
                    break
                except Exception as e:
                    e_ = str(e).replace("\n", "").strip()[:100]
                    exception += f" exception({e_})" if e_ not in exception else ""
                delay = base_delay ** (attempt + 1)
                await asyncio.sleep(delay)
            # return Exception(exception)  # noqa
            rk["exception"] = exception
            return rk

    async def fetch_batch(self):
        proxy = self.proxies["http"] if self.proxies["http"] else None
        async with AsyncClient(proxy=proxy, headers=self.headers) as client:
            tasks = [
                asyncio.create_task(
                    self.fetch(
                        client,
                        extract=["data"],
                        method="get",
                        url=self.url,
                        params=params,
                    )
                )
                for params in self.params_batch
            ]
            for task in asyncio.as_completed(tasks):
                item = await task
                url: str = item["url"]
                params: dict = item["params"]
                symbol = params["symbol"]
                t = self.time_interval_reverse.get("-".join([params["interval"], params["limit"]]))
                if exception := item.get("exception"):
                    self.exceptions[f"{self.name}_{symbol}_{t}"] = item
                    self._print(f"[{self.name}] Symbol({params['symbol']}) Type({t}): {exception}", "warn")
                    continue
                result: str = item["result"]
                if data := decrypt_from_app(
                        url.replace(self.domin, ""),
                        result
                ):
                    await self.upload_queue.put(
                        Liquidation(
                            symbol=symbol,
                            type=t,
                            data=data
                        ).to_dict()
                    )
                else:
                    self._print(f"[{self.name}] Symbol({params['symbol']}) Type({t}) not data")

    @auto_execute_method()
    async def liq_heat_map_tra_pair_model_2(self):
        await self.fetch_all_exchange_trading_pairs()
        self._print(f"[{self.name}] trading_pairs({len(self.trading_pairs)})")
        await self.init_params_batch()
        self._print(f"[{self.name}] fetch batch [{len(self.params_batch)}] tasks")
        await self.fetch_batch()


async def func_test():
    async def check_upload_result(func_upload):
        async for item in func_upload():
            print(s if len(s := json.dumps(item)) < 300 else s[:300] + "...")
            print(f"upload_result {len(item['liq_heat_map_tra_pair_model_2'])} items")

    project = LiqHeatMapTraPairModel2(**kw)
    async with asyncio.TaskGroup() as tg:
        tg.create_task(project.process())
        tg.create_task(check_upload_result(project.upload_result))


if __name__ == '__main__':
    kw = {
        "extra_params": {
            "exchanges": ["binance"],
            "time_interval": [
                # "12h",
                "1d",
                # "2d"
            ],
            "tra_pairs": ["BTCUSDT"]
        },
    }

    asyncio.run(async_func_test(LiqHeatMapTraPairModel2, kw))

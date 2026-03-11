from dataclasses import dataclass

from weist_spider_project.utils.models import BaseModel


@dataclass
class Liquidation(BaseModel):
    symbol: str = None  # 交易对或币种： "BTC"
    type: str = None  # 类型或时间
    data: dict = None  # 数据

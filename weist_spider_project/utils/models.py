# -*- coding: utf-8 -*-
# @Author:      weist
# @Date:        2026/-/- 00:00
# @File:        .py
# @Software:    PyCharm
# @Description: 模型文件
from dataclasses import fields, is_dataclass


def auto_cast(self):
    for f in fields(self):
        value = getattr(self, f.name)
        if value is not None:
            try:
                setattr(self, f.name, f.type(value))
            except Exception as e:
                pass  # 转换失败就跳过


class BaseModel:

    def __post_init__(self):
        auto_cast(self)

    def to_dict(self):
        return {k: v.to_dict() if is_dataclass(v) else v for k, v in self.__dict__.items() if v is not None}

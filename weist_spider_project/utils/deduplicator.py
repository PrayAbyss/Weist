# -*- coding: utf-8 -*-
# @Author:      Weist
# @Date:        2025/4/30 10:52
# @File:        MilvusDeduplicator.py
# @Software:    PyCharm
# @Description: Milvus数据库查重
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
score_round = 0.75


class MilvusDeduplicator:
    db = None

    def __init__(
            self,
            *args,
            **kwargs
    ):
        pass

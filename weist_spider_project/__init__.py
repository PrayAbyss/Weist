# -*- coding: utf-8 -*-
# @Author:      weist
# @Date:        2026/-/- 00:00
# @File:        __init__.py
# @Software:    PyCharm
# @Description:

import os
import sys

BASE_PATH = os.path.abspath(os.path.dirname(__file__))
PROJECT_PATH = os.path.abspath(os.path.join(BASE_PATH, '..'))
sys.path.append(PROJECT_PATH) if PROJECT_PATH not in sys.path else None

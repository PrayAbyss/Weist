import logging
import os
from datetime import datetime

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class Logger:
    log_level = logging.INFO
    log_name = None
    log_formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    def __init__(self, *args, **kwargs):
        log_status = kwargs.get('log_status', True)
        self.log_name = kwargs.get('log_name')
        self.log_dir = kwargs.get('log_dir', os.path.join(BASE_PATH, 'logs'))
        self.formatted_date = kwargs.get('formatted_date', datetime.now().strftime("%Y%m%d"))
        log_name = self.__class__.__name__ if not self.log_name else self.log_name
        # 获取类级别的日志记录器
        self.log = logging.getLogger(log_name)
        # 在类内部设置日志级别
        self.log.setLevel(logging.DEBUG)
        # 避免重复添加 handler（重要）
        if log_status and not self.log.handlers:
            # 控制台 handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # 文件 handler
            log_dir = os.path.join(self.log_dir, f"{self.formatted_date}")
            os.makedirs(log_dir, exist_ok=True)
            log_path = os.path.join(log_dir, f'{log_name}.log')
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)

            # 格式
            formatter = logging.Formatter(self.log_formatter)
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)

            self.log.addHandler(console_handler)
            self.log.addHandler(file_handler)
            self._handlers = [console_handler, file_handler]
            self.log.info(f"log is saved at [{log_path}]")

    def close_log(self):
        if self.log:
            self.log.info(f"log [{self.log_name}] is closed...")
        for handler in getattr(self, '_handlers', []):
            handler.flush()
            handler.close()
            self.log.removeHandler(handler)
        self._handlers = []


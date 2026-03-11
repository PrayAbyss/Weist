import os

from utils.core import Dispatcher

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


class CrawlLiquidation(Dispatcher):
    name = "crawl_liquidation"

    def __init__(self, *args, **kwargs):
        kwargs_ = {}
        kwargs_.update(kwargs)
        kwargs_.update(
            {
                "name": self.name,
                "package_root_path": BASE_PATH,
                "crawl_settings": f"{self.name}.json",
            }
        )
        super().__init__(*args, **kwargs_)


if __name__ == '__main__':
    k = {
        "env": "local"
    }
    project = CrawlLiquidation(**k)
    project.crawl()

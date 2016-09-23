import threading
import logging

from .router import Router
from .config import config
from .worker import create_worker

response = threading.local()


class Spider(object):
    def __init__(self, start_url):
        self._update_log_basic_config()

        self.r = Router()

        queue_type = config['base']['queue']
        if queue_type == 'simple':
            from .queue import SimpleQueue
            self.task_queue = SimpleQueue()
        elif queue_type == 'redis':
            from .queue import RedisQueue
            self.task_queue = RedisQueue()

        self.task_queue.push_url(start_url)

    def route(self, url):
        def _wrapper(func):
            self.r.add(url, func)

        return _wrapper

    def proxy(self, func):
        self.get_proxy = func

        def _wrapper():
            return func()

        return _wrapper

    def run(self):
        worker = config['base']['worker']
        for i in range(worker):
            threading.Thread(target=create_worker(self, response))

    def _update_log_basic_config(self):
        level_dict = {
            "debug": logging.DEBUG,
            "info": logging.INFO,
            "warning": logging.WARNING,
            "error": logging.ERROR,
            "critical": logging.CRITICAL
        }
        level = level_dict[
            config.get('log', 'level', fallback='info').lower()
        ]

        kwargs = {
            "level": level,
            "format": '[%(asctime)s - %(levelname)s - %(name)s] - %(message)s'
        }

        display = config.get('log', 'display', fallback='console')
        if display == 'file':
            filename = config.get('log', 'filename')
            kwargs['filename'] = filename

        logging.basicConfig(**kwargs)

    def filter(self, include=None, exclude=None):
        if include:
            for url in include:
                self.r.add(url, filter_type='include')

        if exclude:
            for url in exclude:
                self.r.add(url, filter_type='exclude')

    def priority(self):
        def _wrapper(func):
            self.get_proxy = func

        return _wrapper

    def get_priority(self, url=None):
        level = 0
        if self.r.search(url):
            return 100

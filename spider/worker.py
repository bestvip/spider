from urllib.parse import urlparse, urljoin
import time

import requests
from lxml import etree

from .config import config
from .logger import logger


def create_worker(work_id, spider, response):
    router = spider.r
    task_queue = spider.task_queue

    config_proxy = config['base'].get('proxy', False)
    max_try_times = config['base'].get('max_try_times', 0)
    sleeptime = config['base'].get('sleeptime', 0)

    headers = config['headers']

    kwargs = {
        "headers": headers
    }

    log = logger.get_logger('work-{id}'.format(id=work_id))

    def worker():
        if sleeptime:
            time.sleep(sleeptime)
        log.info('start worker {0}'.format(work_id))
        while True:
            task = task_queue.pop_task()
            if task is None:
                continue
            node, args = router.get_node(task.url)
            # todo: filter

            if config_proxy:
                proxy = spider.get_proxy()
                kwargs['proxies'] = proxy.get_proxies()

            try:
                log.info('start download page : {url}'.format(url=task.url))
                r = requests.get(task.url, **kwargs)
                log.info('download page success : {url}'.format(url=task.url))
            except ConnectionError as e:
                log.debug(
                    'download page error, retry again : {url}'.format(url=task.url))
                task.try_times += 1
                if task.try_times == max_try_times:
                    log.debug('max try times : {url}'.format(url=task.url))
                    continue

                spider.push_task(task)

            if r.status_code < 200 or r.status_code >= 400:
                continue

            tree = etree.HTML(r.text)
            result = tree.xpath('//a')

            for item in result:
                href = item.attrib.get('href')
                sub_url = convert(href, task.url)
                if sub_url:
                    task_queue.push_url(sub_url)

            if node and node.func:
                response.response = r
                node.func(**args)

    return worker


def convert(href, url):
    href = urljoin(url, href)

    url_result = urlparse(url)
    href_result = urlparse(href)

    if href_result.netloc == url_result.netloc and href_result.scheme == url_result.scheme:
        return href
    else:
        return None

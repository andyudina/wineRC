import re
import asyncio
from asyncio import JoinableQueue as Queue

import requests
import tarantool
from bs4 import BeautifulSoup as bs

from lib.models import Wine
from settings import DOMAIN, TARANTOOL_CONNCTION, CHUNK_LENGTH

CATALOG_PATH = '/catalog/vino/'
CRAWLER_MAX_WORKERS = 10
SUCCESS_STATUS_CODES = [200, 202, ]
MAX_PAGE = 1000

TNT_INSERT_CHUNK = 2
class SimpleWineCrawler:
    def __init__(self):
        self.catalog_pages_queue = Queue()
        self.wines = Wine.load_all()
         
    @asyncio.coroutine    
    def crawl(self):
        workers = [asyncio.Task(self.work_on_catalog_pages())
                  for _ in range(CRAWLER_MAX_WORKERS)]
        yield from self.catalog_pages_queue.put(('catalog', 1)) # start collecting wines from first catalog page
        yield from self.catalog_pages_queue.join()
        for w in workers:
            w.cancel()

    def _extract_wine_info(self, content): #raises ValueError on broken description
        def _extract_td_by_number(tr, td_number):
            try:
                return tr.find_all('td')[td_number].text.strip()
            except (AttributeError, IndexError):
                return None
                
        #def _extract_2nd_td(tr):
        #    try:
        #        return tr.find_all('td')[1].text.strip()
        #    except (AttributeError, IndexError):
        #        raise ValueError

        #def _extract_2nd_td_conditionally(expected_name, tr):
        #    try:
        #        if tr.find_all('td')[0].text.strip() != expected_name:
        #            print(tr.find_all('td')[0].text)
        #            print(expected_name)
        #            raise ValueError
        #        return tr.find_all('td')[1].text
        #    except (AttributeError, IndexError):
        #        raise ValueError
                
        def _get_by_index(list_, index):
            try:
                return list_[index]
            except IndexError:
                return None 

        def _tds2hash(td_raws):
            res = {}
            for row in td_raws:
                key = _extract_td_by_number(row, 0)
                value = _extract_td_by_number(row, 1)
                if not key or not value: continue
                res[key] = value
            return res
            
        soup = bs(content, 'html.parser')
        name = soup.select_one('h1.title').text.strip(' \t\n\r'), #name
        wine = self.wines.get(name[0])
        if not wine:
            print(name) 
            return
         
        wine.price = soup.select_one('.item-buy__prize').attrs.get('data-price')
         
        # features -- extended description
        extra_info_bag_of_words = _tds2hash(
            soup.select_one('#characteristics .tabs-content__table.padding').find_all('tr')
        )
        wine.food = extra_info_bag_of_words.get('Гастрономия:').strip(' \t\n\r') #gastronomy
        if not wine or not wine.food: print(wine.name)
        return wine 

    def _save_wine2tnt(self, wine):
        wine.replace()


    @asyncio.coroutine
    def work_on_catalog_pages(self):
        while True:
            data = yield from self.catalog_pages_queue.get()
          
            if data[0] == 'wine':
                yield from self._process_catalog_link(data[1])
            elif data[0] == 'catalog':
                yield from self._process_catalog_page(data[1])
            self.catalog_pages_queue.task_done()

    @asyncio.coroutine
    def _process_catalog_link(self, url_path):
        print('process link: ' + url_path)
        r = requests.get(DOMAIN + url_path)
        if r.status_code not in SUCCESS_STATUS_CODES:
            # its ok to loose some wines
            return 
        try:
            wine = self._extract_wine_info(r.text)
        except (ValueError, TypeError):
            return
        if wine:
            self._save_wine2tnt(wine)
        
    def _get_next_catalog_page(self, page=None):
        if page and page > MAX_PAGE:
            # don't iterate over all pages on test run
            return None
        kwargs = {}
        if page and page > 1:
            kwargs = {'params': {'PAGEN_2': page}}
        r = requests.get(DOMAIN + CATALOG_PATH, **kwargs) 
        if r.status_code not in SUCCESS_STATUS_CODES:
            return None
        return r.text
  
    @asyncio.coroutine 
    def _process_catalog_page(self, page):
        print('processing page: ' + str(page))
        catalog_page = self._get_next_catalog_page(page)
        if not catalog_page:
            return
        catalog_links = self._get_all_catalog_links_from_page(catalog_page)
        for link in catalog_links:
            yield from self.catalog_pages_queue.put(('wine', link))     
        yield from self.catalog_pages_queue.put(('catalog', page + 1))

    def _get_all_catalog_links_from_page(self, page):
        soup = bs(page, 'html.parser')
        return [category['href'] for category in soup.select('.category__item_new__title a') if category['href']]


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    crawler = SimpleWineCrawler()
    loop.run_until_complete(crawler.crawl())

import re
import asyncio
#from asyncio import JoinableQueue as Queue
from asyncio import Queue
import requests
import tarantool
from bs4 import BeautifulSoup as bs

from settings import DOMAIN, TARANTOOL_CONNCTION, CHUNK_LENGTH

CATALOG_PATH = '/catalog/vino/'
CRAWLER_MAX_WORKERS = 10
SUCCESS_STATUS_CODES = [200, 202, ]
MAX_PAGE = 1

TNT_INSERT_CHUNK = 2
class SimpleWineCrawler:
    def __init__(self):
        self.catalog_pages_queue = Queue()
        self.tnt = self._connect2tarantool()
 
    def _connect2tarantool(self):
        # its ok to fall here --> without connection to storage no need to parse data
        return tarantool.connect(**TARANTOOL_CONNCTION)
        
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
        data_list = [
            soup.select_one('h1.title').text, #name
            soup.select_one('div.item__image img')['src'], #image url --> TODO: download image
        ]

        basic_data = soup.select('.detail_prop_val')
        data_list.extend([
            (_get_by_index(basic_data, 0) and basic_data[0].text), #color
            (_get_by_index(basic_data, 1) and basic_data[1].text), #switness
            ''.join([x.text for x in basic_data[2: -1] if x.text]), #grapes
            (_get_by_index(basic_data, -1) and basic_data[-1].text), #country
        ])  
        
        extra_info = _tds2hash(
            soup.select_one('#characteristics .tabs-content__table').find_all('tr')
        )
        
        # feautures -- short description
        if not extra_info.get('Стилистика:'): raise ValueError #skip wines without description
        
        data_list.extend([
            extra_info.get('Регион:'), #region
            extra_info.get('Крепость:'), #strength
            extra_info.get('Температура подачи от и до:'), #temperature
            extra_info.get('Декантация:'), #decantation 
            extra_info.get('Год:'), #vintage
            extra_info.get('Стилистика:'), #style
            extra_info.get('Выдержка в ёмкости:'), #ageing
        ])
                
        #data_list.extend([
        #    _extract_2nd_td_conditionally('Регион:', _get_by_index(extra_info, 0)), #region
        #    _extract_2nd_td_conditionally('Крепость:', _get_by_index(extra_info, 4)), #strength
        #    _extract_2nd_td_conditionally('Температура подачи от и до:', _get_by_index(extra_info, 5)), #temperature
        #    _extract_2nd_td_conditionally('Декантация:', _get_by_index(extra_info, 8)), #decantation 
        #    _extract_2nd_td_conditionally('Год:', _get_by_index(extra_info, 3)), #vintage
        #    _extract_2nd_td_conditionally('Стилистика:', _get_by_index(extra_info, 10)), #style
        #])
         
        # features -- extended description
        extra_info_bag_of_words = _tds2hash(
            soup.select_one('#characteristics .tabs-content__table.padding').find_all('tr')
        )
        data_list.extend([
            extra_info_bag_of_words.get('Дегустационные характеристики:'), #taste description
            extra_info_bag_of_words.get('Гастрономия:') #gastronomy
        ])
        
        #data_list.append(_extract_2nd_td(_get_by_index(extra_info_bag_of_words, 4))) #taste description
        #data_list.append(_extract_2nd_td(_get_by_index(extra_info_bag_of_words, 1))) #gastronomy
        for i, str_ in enumerate(data_list):
            if str_ is not None:
                data_list[i] = str(str_).strip(' \t\n\r') 
        return data_list

    def _save_wine2tnt(self, data):
        if not hasattr(self, 'tnt') or not self.tnt:
            raise ValueError('no tnt connector')
        try:
            print('saving wine')
            print(data)
            self.tnt.call('wine.insert_local', [data, ])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass #its ok to have duplicate error
 
    def _save_catalog2tnt(self, data):
        if not hasattr(self, 'tnt') or not self.tnt:
            raise ValueError('no tnt connector')
        try:
            self.tnt.call('catalog.insert', [data, ])
        except tarantool.error.DatabaseError:
            pass #its ok to have duplicate error

    def _delete_from_catalog_tnt(self, url):
        if not hasattr(self, 'tnt') or not self.tnt:
            raise ValueError('no tnt connector')
        try:
            self.tnt.call('catalog.delete_by_pk', [url, ])
        except tarantool.error.DatabaseError:
            pass #its ok to have duplicate error

    def _save_links2tnt(self, urls, page):
        if not hasattr(self, 'tnt') or not self.tnt:
            raise ValueError('no tnt connector')
        for i in range(0, len(urls), TNT_INSERT_CHUNK):
            # split data to chunks to prevent tnt stack overflow
            data = [(url, page) for url in urls[i: i + TNT_INSERT_CHUNK]]
            try:
                print('saving data')
                print(data)
                self.tnt.call('catalog.insert', [data, ])
            except tarantool.error.DatabaseError as e:
                print(e)
                pass #its ok to have duplicate error

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
            data = self._extract_wine_info(r.text)
        except ValueError:
            return
        self._save_wine2tnt(data)
        self._delete_from_catalog_tnt(url_path)

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
        self._save_links2tnt(catalog_links, page)
        print(catalog_links)
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

from itertools import product

import tarantool
from lib.models.base import Base

class Wine(Base):
    fields = [
         'name',
         'image_url',
         'color',
         'switness',
         'grape', 
         'country',
         'region',
         'alcohol',
         'serving temperature',
         'decantation',
         'vintage',
         'style',
         'ageing',
         'charateristics',
         'gastronomy',
         'image',
         'temperature_min',
         'temperature_max',
         'words_style',
         'words_characteristics',
         #'words_gastronomy',
         'characteristic_categories',
         'food',
         'price'
    ]
    
    @classmethod
    def load_all(cls):
        print('load all wines')
        raw_wines = cls.get_by_chunks('wine.find_by_chunk')
        return {t[0]: Wine(**cls.tuple2hash(t)) for t in raw_wines}
      
    @classmethod
    def delete_all(cls):
        cls.tnt.call('wine.delete_all', [[]])
          
    def get_category_pairs(self):
        return [list(c) + [self.name, ] for c in product(self.characteristic_categories, repeat=2) if c[0] != c[1]]
        
    def update(self, **kwargs): 
        fields2update = self.fields
        if kwargs.get('fields'):
            fields2update = kwargs.get('fields') 
        values2update = [ 
            [ i + 1, getattr(self, field) ] \
            for i, field in enumerate(self.fields) if field in fields2update
        ]
        try:
            self.tnt.call('wine.update_local', [self.name, ] + values2update)
        except tarantool.error.DatabaseError as e:
            print(e)
            
    def replace(self):
        values2update = Wine.hash2tuple(self.__dict__)
        try:
            #print([self.name, ] + values2update)
            self.tnt.call('wine.replace_local', [values2update])
        except tarantool.error.DatabaseError as e:
            print(e)     

    def delete(self):
        try:
            #print([self.name, ] + values2update)
            self.tnt.call('wine.delete_by_pk', [self.name])
        except tarantool.error.DatabaseError as e:
            print(e)   

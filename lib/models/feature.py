from itertools import product

import tarantool
from pandas import DataFrame

from lib.models.base import Base

class Feature(Base):
    fields = [
         'name',
         'features'
    ]
    
    @classmethod
    def load_all(cls):
        print('load all features')
        features = cls.tnt.call('feature.get_feature_table', [[]]).data
        headers = features[0]
        features = features[1:]
        df = DataFrame(features, columns=headers)
        res = df.groupby('name').sum()
        #print(res)
        return res

    @classmethod
    def tuple2hash(cls, t):
        res = {'_name': t[0]}
        for index, val in enumerate(t[1:]):
            res['feature_' + str(index)] = val
        return res

    @classmethod
    def hash2tuple(cls, hash_):
        keys = sorted(hash_.keys())
        return [ hash_.get(k) for k in keys ]

    @classmethod
    def load_hash(cls):
        raw_features = cls.get_by_chunks('feature.find_by_chunk')
        #print(raw_features)
        return {t[0]: Feature(**cls.tuple2hash(t)) for t in raw_features}

    @classmethod
    def load_all_names(cls):
        print('load all feature names')
        return cls.tnt.call('feature.get_feature_names', [[]]).data[0] 
        
    def insert(self):
        try:
            #print([[self.name, self.features],])
            self.tnt.call('feature.insert_feature', [[self.hash2tuple(self.__dict__)]])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass         

    def delete(self):
        try:
            #print([[self.name, self.features],])
            self.tnt.call('feature.delete', [self._name])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass

    def replace_name(self, name):
        #self.delete()
        self._name = name
        print([self.hash2tuple(self.__dict__)])
        self.insert()

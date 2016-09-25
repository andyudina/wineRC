from itertools import product

from pandas import DataFrame

from models.base import Base

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
    def load_all_names(cls):
        print('load all feature names')
        return cls.tnt.call('feature.get_feature_names', [[]]).data[0] 

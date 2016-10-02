import itertools
import csv
import math

from lib.models import Wine, Feature
            
if __name__ == '__main__':
    wines = Wine.load_all()
    features = list(set(list(itertools.chain.from_iterable(wine.characteristic_categories for wine in wines.values()))))
    #print(list(features)) 
    for wine in wines.values():
        f = Feature(name=wine.name, features=[])
        for feature in features:
            if feature in wine.characteristic_categories:
                f.features.append(1)
            else:
                f.features.append(0)
        f.insert()
            
    Wine.tnt.call('feature.replace_feature_names', [[features, ]]) 

    
    

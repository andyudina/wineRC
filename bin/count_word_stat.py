import tarantool
from collections import Counter
from sklearn.feature_extraction import DictVectorizer

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH, BAG_OF_WORDS_INDEXES

# 1: name: str
# 2: image_url str
# 3: color: red/white/pink str
# 4: switness: dry/sweet/semi-sweet str
# 5: grape str
# 6: country str
# 7: region str
# 8: alcohol str -> num
# 9: serving temperature str
# 10: decantation str
# 11: vintage num
# 12: ageing str

# [need to be treated as bag of words]
# 13: style
# 14: charateristics
# 15: gastronomy

#[postprocessed results]
# 16: downloaded photo name
# 17: temperature min
# 18: temperature max
# 19: bag of words_style
# 20: bag of words_characteristics
# 21: bag of words_gastronomy

def find_words_fequences__total(y, x):
    # считаем каждое вхождение, в т.ч. и в одном описании
    pass
    
def find_words_frequences__by_wine(y, x):
    #одно вхождение == одно упоминание в описании вина
    pass
 
def find_tdf_if(y, x):
    pass

def _words2counts_dict(word_lits):
    return dict(Counter(word_lits))
    
def tuples2dict_features(tuples):
    res = [[], [], []]
    for t in tuples:
        for i, word_list in enumerate(t[18: 21]):
            res[i].append(_words2counts_dict(word_list))
    return res

def split_tuples2features(tuples):
    y = [[t[0]] for t in tuples]
    x = []
    features = []
    dict_features = tuples2dict_features(tuples)
    for feature_set in dict_features:
        vec = DictVectorizer()
        x.append(
            vec.fit_transform(feature_set).toarray()
        )
        features.append(
            vec.get_feature_names()
        )
    return y, x, features
    
       
 
def _apply2all_word_collections(y, x, func):
    res = {}  
    for word_collection in ['style', 'characteristics', 'gastronomy']:
        res[word_collection] = func(y, x[word_collection])
    return res
             
def count_word_stat():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    
    result_tuples = []
    while len(tuples) > 0 and tuples[0]:
        result_tuples.extend(tuples)
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
        
    x = {}
    features = {}
    y, \
    [x['style'], x['characteristics'], x['gastronomy']], \
    [features['style'], features['characteristics'], features['gastronomy']] = split_tuples2features(result_tuples)
    
    print(y)
    print(x)
    print(features)
    #stat_collectors = [find_words_fequences__total, find_words_frequences__by_wine, find_tdf_if]
    
    #for collector in stat_collectors:
    #    _apply2all_word_collections(y, x, collector)    
    
     
if __name__ == '__main__':
    count_word_stat()


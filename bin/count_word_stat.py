from itertools import chain, product
from collections import Counter
import csv

import tarantool
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfTransformer

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH, BAG_OF_WORDS_INDEXES

BAG_OF_WORDS_TYPE2ORDER = {
    'style': 18,
    'characteristic': 19,
    'gastronomy': 20,
    'style_pairs': 21,
    'characteristics_pairs': 22,
    'gastronomy_pairs': 23,
    'style_pairs_row': 24,
    'characteristics_pairs_row': 25,
    'gastronomy_pairs_row': 26 
}

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

def _flatten_bag_of_words(tuples, extract_func):
    return chain.from_iterable(extract_func(t) for t in tuples)
  
def _count_accuracies(word_list):
    return dict(Counter(word_list))
      
def find_words_fequences__total(tuples, keys2order):
    # считаем каждое вхождение, в т.ч. и в одном описании
    res = {}
    for key, order in keys2order.items():
        print('finding total accurency 4 {}'.format(key))
        res[key] = _count_accuracies(
            _flatten_bag_of_words(
                tuples,
                lambda x: x[order]
            )
        )
        #print(res[key])
    return res
    
def find_words_frequences__by_wine(tuples, keys2order):
    #одно вхождение == упоминание в описании вина
    res = {}
    for key, order in keys2order.items():
        print('finding accurency by wine {}'.format(key))
        res[key] = _count_accuracies(
            _flatten_bag_of_words(
                tuples,
                lambda x: list(set(x[order]))
            )
        )
        #print(res[key])
    return res
 
def _find_tf_idf(x):
    #import gc; gc.collect() #to prevent MemoryError
    res = TfidfTransformer().fit_transform(x).max(axis=0).todense().tolist()
    return res[0]
    
def find_word_tf_idf_metric(x, features):
    res = {}
    for key, counters in x.items():
        print('estimating tf-idf {}'.format(key))
        counters = _find_tf_idf(counters)
        #print(counters)
        #print(features[key])
        res[key] = dict(
            zip(
                features[key], counters 
            )
        )
    return res
     
def _words2counts_dict(word_lits):
    return dict(Counter(word_lits))
    
def _tuples2dict_features(tuples, extract_features_func):
    res = [[], [], [], [], [], [], [], [], [] ]
    for t in tuples:
        #print(extract_features_func(t))
        for i, word_list in enumerate(extract_features_func(t)):
            res[i].append(_words2counts_dict(word_list))
    return res

def split_tuples2features(tuples, extract_features_func):
    y = [[t[0]] for t in tuples]
    x = []
    features = []
    dict_features = _tuples2dict_features(tuples, extract_features_func)
    for feature_set in dict_features:
        vec = DictVectorizer()
        x_ = vec.fit_transform(feature_set)#.toarray()
        x.append(
            x_
        )
        f_ = vec.get_feature_names()
        features.append(
            f_
        )
        #print(f_)
    return y, x, features      

def _find_min_max(keys2order):
    orders = keys2order.values()
    return [min(orders), max(orders)]
    
def estimate_word_stat(tuples, keys2order):
    wc_total = find_words_fequences__total(tuples, keys2order)
    wc_by_wine = find_words_frequences__by_wine(tuples, keys2order)

    min_order, max_order = _find_min_max(keys2order)
    x_ = []
    f_ = []
    y, x_, f_ = split_tuples2features(tuples, lambda x: x[min_order: max_order + 1])
     
    x = {}
    features = {}
    MIN_ORDER = 18
    
    for key, order in BAG_OF_WORDS_TYPE2ORDER.items():
        x[key] = x_[order - MIN_ORDER]
        features[key] = f_[order - MIN_ORDER]
             
    tf_idf = find_word_tf_idf_metric(x, features)
    
    return {
        'wc_total': wc_total,
        'word_by_wine': wc_by_wine,
        'tf_idf': tf_idf
    }       

def _generate_all_word_pairs(words):
    return [' '.join(sorted(p)) for p in product(words, words) if p[0] != p[1]]

def _generate_all_word_pairs_in_row(words):
    return [' '.join(sorted([words[i], words[i + 1]])) for i in range(len(words) - 1)]
   
def add_word_pairs(tuples):
    print('adding pairs')
    for t in tuples:
        for order in BAG_OF_WORDS_INDEXES:
            t.append(_generate_all_word_pairs(t[order]))        
    #print(tuples)
    
def add_word_pairs_in_row(tuples):
    print('adding pairs in rows')
    for t in tuples:
        for order in BAG_OF_WORDS_INDEXES:
            t.append(_generate_all_word_pairs_in_row(t[order])) 
    #print(tuples) 

def _save_data2csv(f, features):
    with open(f, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        for feature in features:
            writer.writerow(feature)

def _features2csv(feature_dict):
    return sorted(feature_dict.items(), key=lambda x: x[1])
                
def save2csv(res):
    for stat_key, stat in res.items():
        for feature_key, features in stat.items():
            features = _features2csv(features)
            file_name = 'csv/{}__{}.csv'.format(stat_key, feature_key)
            _save_data2csv(file_name, features)
                                   
def count_word_stat():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    
    result_tuples = []
    while len(tuples) > 0 and tuples[0]:
        result_tuples.extend(tuples)
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
        
    add_word_pairs(result_tuples)
    add_word_pairs_in_row(result_tuples)    
    
    res2csv = estimate_word_stat(result_tuples, BAG_OF_WORDS_TYPE2ORDER)
    #print(res2csv)
    save2csv(res2csv)
    
     
if __name__ == '__main__':
    count_word_stat()


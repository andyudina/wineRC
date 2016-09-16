import datetime
import re
import shutil
import hashlib # for picture filename
import collections
from itertools import chain
 
import requests
import nltk
import tarantool
import pymorphy2

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH, YANDEX_BASE_URL, YANDEX_DICT_KEY

SUCCESS_STATUS_CODE = 200
MIN_WORD_LENGTH = 3
MIN_COMMON_RATIO = 0.5
BAG_OF_WORDS_INDEXES = [18, 19, 20]

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

morph = pymorphy2.MorphAnalyzer()
def _get_normal_form(word):
    parsed_word = morph.parse(word)[0]
    if not parsed_word: return word
    return (parsed_word.normal_form or word)
    
def _get_synonyms(word):
    #TODO: to normal form
    word = _get_normal_form(word)
    url = YANDEX_BASE_URL.format(YANDEX_DICT_KEY, word)
    r = requests.get(url)
    if r.status_code != SUCCESS_STATUS_CODE:
        print(r.status_code)
        return []
    response = r.json()
    try:
        return [w['text'] for w in response['def'][0]['tr'][0]['syn']]
    except (KeyError, IndexError):
        print(response)
        print(word)
        return []
        
def _merge_and_label_synonyms_groups(synonyms):
    def _syn_hash2sets(syn_hash):
        result = []
        for word, synonyms in syn_hash.items():
            if not synonyms: continue
            result.append(set(synonyms + [word, ]))
        return result
            
    def _are_mergable(source_word_set, dest_word_set):
        common = list(source_word_set & dest_word_set) 
        source_word_set = list(source_word_set)
        dest_word_set = list(dest_word_set)
        ratios = [len(common) / len(source_word_set), len(common) / len(dest_word_set)]
        if len(filter(lambda x: x > MIN_BOTH_COMMON_RATIO)) >= 1: #merge synonyms if half of one or more bags is in iterception
            return True
        return False 
    
    def _syn_sets2hash(word_sets): 
        res_hash = {}
        for s in word_sets:
            if not s: continue
            label = s[0]
            for word in s:
                res_hash[word] = label
        return res_hash
              
    word_sets = _syn_hash2sets(synonyms)
    for i, source_word_set in enumerate(word_sets[: -1]):
         # find all similiar sets and merge them 
         was_merged = False
         for j, dest_word_set in enumerate(word_sets[i + 1: ]):  
             if _are_mergable(source_word_set, dest_word_set):
                 word_sets[j + i + 1].update(source_word_set)
                 was_merged = True
         if was_merged: 
             word_sets.pop(i)
    print('merged synonyms')
    print(word_sets)         
    return _syn_sets2hash(word_sets)
                
def _replace_words_with_synonyms(t, synonyms):
    print('replace words with synonyms 4 ' + t[0])
    for syn in synonyms.values():
        syn_hash = syn['words']
        order = syn['order']
        if not t[order]: continue
        for i, word in enumerate(t[order]):
            if len(word) < MIN_WORD_LENGTH: 
                t[order].pop(i)
                continue
            t[order][i] = syn_hash.get(word, word)
            
def _update_wine_bag_of_words(syn_t, tnt):
    print('updating tuple')
    print(syn_t)
    tnt.call(
        'catalog.delete_by_pk', 
        [syn_t[0], list(chain.from_iterable((index, syn_t[index]) for index in BAG_OF_WORDS_INDEXES))]
    )
 
def _stemm_tuple(t):
    for t_order in range(18, 21):
        t[t_order] = _stemm_words(t[t_order])
        
def _stemm_words(tokenized_text):
    if not tokenized_text: return []
    stemmer = nltk.stem.snowball.RussianStemmer(ignore_stopwords=True)
    stemmed_text = []
    for word in tokenized_text: 
        stem = stemmer.stem(word)
        if stem and len(stem) > 2: #skip short words
            stemmed_text.append(stem)
    return stemmed_text
                   
def _collect_synonyms(synonyms, t):
    print('collecting synonyms 4 ' + t[0])
    for key, info in synonyms.items():
        bag_of_words = t[info['order']]
        print(t)
        print(info['order'])
        if not bag_of_words: continue
        for word in bag_of_words:
            if len(word) < MIN_WORD_LENGTH: continue
            if info['words'].get(word): continue
            synonyms[key]['words'][word] = _get_synonyms(word)
              
    
 
def process_wine_synonyms():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    synonyms = {
       'style': {
           'words': {},
           'order': 18
       },
       'characteristics': {
           'words': {},
           'order': 19
       },
       'gastronomy': {
           'words': {},
           'order': 20
       }       
    }
    result_tuples = []
    while len(tuples) > 0 and tuples[0]:
        result_tuples.extend(tuples)
        for t in tuples:
            _collect_synonyms(synonyms, t)
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data 
    
    print('total synonyms')
    print(synonyms)
    for key, info in synonyms.items():
        synonyms[key]['words'] = _merge_and_label_synonyms_groups(synonyms[key]['words'])
        
    for t in result_tuples:
        syn_t = _replace_words_with_synonyms(t, synonyms)
        _stemm_tuple(t)
        _update_wine_bag_of_words(syn_t, tnt)
    
if __name__ == '__main__':
    process_wine_synonyms()


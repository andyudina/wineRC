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

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH, YANDEX_BASE_URL, YANDEX_DICT_KEY, BAG_OF_WORDS_INDEXES

SUCCESS_STATUS_CODE = 200
MIN_WORD_LENGTH = 3
MIN_COMMON_RATIO = 0.5
COMPLEX_BAG_OF_WORDS_INDEXES = [19, 20] #style обрабатываем как единичную фичу
BANNED_PARTS2ORDER = {
    19: [
        'VERB',  # глагол (личная форма)
        'COMP',  # компаратив
        'INFN',  # глагол (инфинитив)
        'PRTF',  # причастие (полное)
        'PRTS',  # причастие (краткое)
        'GRND',  # деепричастие
        'NUMR',  # числительное
        'ADVB',  # наречие
        'NPRO',  # местоимение-существительное
        'PRED',  # предикатив
        'PREP',  # предлог
        'CONJ',  # союз
        'PRCL',  # частица
        'INTJ',  # междометие
        ],
    20: [
        'ADJF',  # имя прилагательное (полное)
        'ADJS',  # имя прилагательное (краткое)
        'COMP',  # компаратив
        'VERB',  # глагол (личная форма)
        'INFN',  # глагол (инфинитив)
        'PRTF',  # причастие (полное)
        'PRTS',  # причастие (краткое)
        'GRND',  # деепричастие
        'NUMR',  # числительное
        'ADVB',  # наречие
        'NPRO',  # местоимение-существительное
        'PRED',  # предикатив
        'PREP',  # предлог
        'CONJ',  # союз
        'PRCL',  # частица
        'INTJ',  # междометие
    ]
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
def _is_number(val):
   try:
       int(val)
       return True
   except (ValueError, TypeError):
       return False

def _has_non_alphanumeric_symobls(word):
    return not not re.match(r'\W+', word)
           
russian_stop_words = list(nltk.corpus.stopwords.words('russian'))
def _rm_stop_words(words, custom_stop_words=[]):
    #first iteration: rm stop words except 'не'
    for i, word in enumerate(words):
         if (_is_number(word) or \
             _has_non_alphanumeric_symobls(word) or \
             word in russian_stop_words or \
             word in custom_stop_words or len(word) < MIN_WORD_LENGTH) and word != 'не':
             words.pop(i)
    return words
    
def _merge_negation(words):
    #second iteration: merge negation
    for i, word in enumerate(words):
        if word == 'не':
            if i < len(words) - 1: 
                words[i + 1] = ' '.join(words[i: i + 2])     #if its not last word -- merge it with next one
            words.pop(i) #just pop it
    return words
    
def _rm_short_words(words):
    _rm_stop_words(words)
    _merge_negation(words)        
    return words
                
def _rm_short_words4tuple(t):
    for index in BAG_OF_WORDS_INDEXES:
        t[index] = _rm_short_words(t[index])
    return t
        
def _count_unique_words(bag_of_words):
    # expects tuples of format [[word1, word2, word3], [word4, word5], ...]
    return len(list(set(chain.from_iterable(bag_of_words))))

def _assess_unique_words_in_tuples(tuples):
    # посчитать кол-во уникальных слов таплах
    result_counters = {}
    for index in BAG_OF_WORDS_INDEXES:
        result_counters[index] = _count_unique_words(
            [t[index] for t in tuples]
        )
    return result_counters

def _save_synonyms2tnt(synonyms, tnt):
    for info in synonyms.values():
        for word, w_synonyms in info['words'].items():
            tnt.call(
               'synonyms.upsert_local', 
               [[word, w_synonyms]]
            )  
                          
morph = pymorphy2.MorphAnalyzer()
def _is_banned_part_of_speach(parsed_word, banned_parts_of_speach):
    # решить, есть ли часть речи слова в banned_parts_of_speach
    if not parsed_word or not parsed_word.tag: return False
    for pos in banned_parts_of_speach:
        if pos.upper() in parsed_word.tag: return True
    return False
    
def _rm_part_of_speach_and_translate_to_nf(word_list, banned_parts_of_speach):
    for i, word in enumerate(word_list):
        parsed_word = morph.parse(word)[0]
        if _is_banned_part_of_speach(parsed_word, banned_parts_of_speach):
            word_list.pop(i)
        else:
            word_list[i] = (parsed_word.normal_form or word)
    return word_list
            
def _get_normal_form(word):
    # получить нормальную форму (Именительный падеж, единственное число) слова
    parsed_word = morph.parse(word)[0]
    if not parsed_word: return word
    return (parsed_word.normal_form or word)
    
def _get_synonyms(word):
    # скачать все синонимы для слова из яндекса
    url = YANDEX_BASE_URL.format(YANDEX_DICT_KEY, word)
    r = requests.get(url)
    if r.status_code != SUCCESS_STATUS_CODE:
        return []
    response = r.json()
    synonyms = []
    
    # вытащить все синонимы для всех определений ('def') из яндекса
    if not response['def']: 
        return synonyms
        
    for defenition in response['def']:
        if not defenition.get('tr'): continue 
        for tr in defenition.get('tr'):
            if not tr.get('syn'): continue
            synonyms.extend([w['text'] for w in tr.get('syn')])
    return synonyms
        
def _merge_and_label_synonyms_groups(synonyms):
    # склеить группы синонимов
    def _syn_hash2sets(syn_hash):
        # из словаря синонимов сделать лист сетов с лейблами
        result = []
        for word, synonyms in syn_hash.items():
            if not synonyms: continue
            result.append({
                'words': set(synonyms + [word, ]),
                'label': word
            })
        return result
            
    def _are_mergable(source_word_set, dest_word_set):
        # решить, можно ли склеить два сета
        # модем, если на 50% совпадают
        common = list(source_word_set & dest_word_set) 
        source_word_set = list(source_word_set)
        dest_word_set = list(dest_word_set)
        ratios = [float(len(common)) / len(source_word_set), float(len(common)) / len(dest_word_set)]
        if len(list(filter(lambda x: x > MIN_COMMON_RATIO, ratios))) >= 1: 
            #merge synonyms if half of one or more bags is in iterception
            return True
        return False 
    
    def _syn_sets2hash(word_sets): 
        # из массова сетов синонимов сделать словарь для замены слова лейблом группы синонимов
        res_hash = {}
        for s in word_sets:
            if not s['words']: continue
            for word in s['words']:
                res_hash[word] = s['label']
        return res_hash
              
    word_sets = _syn_hash2sets(synonyms)
    for i, source_word_set in enumerate(word_sets[: -1]):
         # find all similiar sets and merge them 
         # слить текущий сет синонимов с похождими сетами
         was_merged = False
         for j, dest_word_set in enumerate(word_sets[i + 1: ]):  
             if _are_mergable(source_word_set['words'], dest_word_set['words']):
                 word_sets[j + i + 1]['words'].update(source_word_set['words'])
                 was_merged = True
         if was_merged: 
             # удалить сет, если слили его хоть с одним
             word_sets.pop(i)
             
    return _syn_sets2hash(word_sets)
                
def _replace_words_with_synonyms(t, synonyms):
    # заменить слова тапла синонимом
    for syn in synonyms.values():
        syn_hash = syn['words']
        order = syn['order']
        if not t[order]: continue
        for i, word in enumerate(t[order]):
            if len(word) < MIN_WORD_LENGTH: # выкинуть все лсова маеньше трешхолда
                t[order].pop(i)
                continue
            # заменить каждое слово лейблом синонимов из словаря
            t[order][i] = syn_hash.get(word, word)
    return t
            
def _update_wine_bag_of_words(t, tnt):
    # сохрнаить новые таплы в тарантул
    #print(t)
    tnt.call(
        'wine.update_local', 
        [t[0], list(chain.from_iterable((index + 1, t[index]) for index in BAG_OF_WORDS_INDEXES))]
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
    # собрать синонимы для всех слов тапла
    # положить в dict synonyms['style']['words']
    for key, info in synonyms.items():
        bag_of_words = t[info['order']] 
        if not bag_of_words: continue 
        for word_index, word in enumerate(bag_of_words):
            if len(word) < MIN_WORD_LENGTH: continue # выкидываем маленькие слова
            if info['words'].get(word): continue #не ходим повторно за синонимами к одному и тому же слову
            word = _get_normal_form(word)
            bag_of_words[word_index] = word
            synonyms[key]['words'][word] = _get_synonyms(word)
              
    
def _clean_bag_of_words(t):
    for order in COMPLEX_BAG_OF_WORDS_INDEXES:  
        # убрать стоп слова
        t[order] = _rm_stop_words(t[order])
        # вычистить неугодные части речи
        t[order] = _rm_part_of_speach_and_translate_to_nf(t[order], BANNED_PARTS2ORDER[order])
        # склеить не
        t[order] = _merge_negation(t[order])
    return t
     
def process_wine_synonyms():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    synonyms = {
       'style': {
           'words': {},
           'order': 18
       },
       #'characteristics': {
       #    'words': {},
       #    'order': 19
       #},
       #'gastronomy': {
       #    'words': {},
       #    'order': 20
       #}       
    }
    result_tuples = []
    while len(tuples) > 0 and tuples[0]:
        result_tuples.extend(tuples)
        #for t in tuples:
        #    _collect_synonyms(synonyms, t)
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
         
    _save_synonyms2tnt(synonyms, tnt)
    for key, info in synonyms.items():
        synonyms[key]['words'] = _merge_and_label_synonyms_groups(synonyms[key]['words'])
       
    print('before synonyms')
    print(_assess_unique_words_in_tuples(result_tuples))
    for t in result_tuples:
        #TODO: return stem process
        #TODO: return synonyms
        #t = _replace_words_with_synonyms(t, synonyms)
        #t = _rm_short_words4tuple(t)
       
        t = _clean_bag_of_words(t)
        #TODO: rm debug
        #if t[0] == 'Вино Warre`s Otima 20 Year Old Tawny Port, 0.5 л.': print(t)
        #TODO: return stemming
        #_stemm_tuple(t)
        #_update_wine_bag_of_words(t, tnt)
        _update_wine_bag_of_words(t, tnt)
    print('after synonyms')
    print(_assess_unique_words_in_tuples(result_tuples))
        
if __name__ == '__main__':
    process_wine_synonyms()


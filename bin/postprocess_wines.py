import datetime
import re
import shutil
import hashlib # for picture filename
import collections

import requests
import nltk
import tarantool

from settings import DOMAIN, TARANTOOL_CONNCTION, CHUNK_LENGTH

EXPECTED_TUPLE_LENGTH = 21
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


def _download_and_save_photo(wine_tuple):
    if not wine_tuple[1]:
        return
        
    r = requests.get(DOMAIN + wine_tuple[1], stream=True)
    photo_filename = hashlib.sha224(wine_tuple[0].encode('utf-8')).hexdigest() + '.png'
    path = '../media/' + photo_filename
    if r.status_code == 200:
        with open(path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)    
        wine_tuple[15] = photo_filename
        
def _process_and_update_simple_text_fields(wine_tuple):
    for field_index in list(range(2, 7)) + list(range(9, 12)):
        if wine_tuple[field_index]:
            wine_tuple[field_index] = wine_tuple[field_index].lower()

def _split_temperature_range2int(wine_tuple):
    temperature_range = wine_tuple[8]
    if not temperature_range: return
    new_range = re.findall(r'\d+', temperature_range)
    if not new_range:
        return 
    if len(new_range) > 2:
        new_range = new_range[:2]
    if len(new_range) < 2:
        new_range.append(new_range[0])
    wine_tuple[16], wine_tuple[17] = new_range[0], new_range[1]    

def _split_grapes2table(wine_tuple):
    grapes = wine_tuple[4]
    if not grapes: return
    wine_tuple[4] = [g.strip() for g in grapes.split(',')]
    
def _change_produced_year2vintage(wine_tuple):
    produced_year = wine_tuple[10]
    if not produced_year: return
    wine_tuple[10] = datetime.datetime.now().year - int(wine_tuple[10])

def _convert_alcohol2float(wine_tuple):
    alcohol_percent = wine_tuple[7]
    if not alcohol_percent: return
    alcohol_percent =  re.findall(r'\d+', alcohol_percent) 
    if not alcohol_percent: return
    wine_tuple[7] = alcohol_percent[0]

def _split_texts2bag_of_words(text):
    #text = (wine_tuple[11] or '') + ' ' + (wine_tuple[12] or '') 
    if not text: return []
    tokenized_text = nltk.wordpunct_tokenize(text)
    stemmer = nltk.stem.snowball.RussianStemmer(ignore_stopwords=True)
    stemmed_text = []
    for word in tokenized_text: 
        stem = stemmer.stem(word)
        if stem and len(stem) > 2: #skip short words
            stemmed_text.append(stem)
    #TODO: process synonims here
    return stemmed_text 
    
def _save2tnt(wine_tuple, tnt_connection):
    tnt_connection.call('wine.update_total', [wine_tuple, ])
            
def postprocess_wine(wine_tuple, tnt_connection):
    print('processing wine: ' + wine_tuple[0])
    if len(wine_tuple) < EXPECTED_TUPLE_LENGTH:
        for i in range(len(wine_tuple), EXPECTED_TUPLE_LENGTH):
            wine_tuple.append(None)
            
    _download_and_save_photo(wine_tuple)
    _process_and_update_simple_text_fields(wine_tuple)
    _split_temperature_range2int(wine_tuple)
    _split_grapes2table(wine_tuple)
    _change_produced_year2vintage(wine_tuple)
    _convert_alcohol2float(wine_tuple)
    for text in wine_tuple[12: 15]:
        wine_tuple.append(_split_texts2bag_of_words(text))
    
    print('result tuple')
    print(wine_tuple)
    _save2tnt(wine_tuple, tnt_connection)
    
 
def postprocess_wines():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, True ]).data
    while len(tuples) > 0 and tuples[0]:
        for t in tuples:
            try:
                postprocess_wine(t, tnt)  
            except (ValueError, IndexError, TypeError):
                # these errors endicates that format of wine is corrupted - we can just discard this wines
                # or that we iterated over all elments in msgpack tuple and reached elem number
                if isinstance(t, collections.Iterable) and len(t): #if elem is corrupted
                    tnt.call('wine.delete_by_pk', [t[0], ]) 
                # else just pass to next chunk
                 
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, True ]).data 
    
if __name__ == '__main__':
    postprocess_wines()


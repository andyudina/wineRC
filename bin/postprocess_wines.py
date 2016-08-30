import datetime
import re
import shutil
import hashlib # for picture filename

import requests

from settings import DOMAIN

# wine space
# 1: name: str
# 2: color: red/white/pink str
# 3: switness: dry/sweet/semi-sweet str
# 4: grape str
# 5. country str
# 6: region str
# 7: alcohol str --> float
# 8: serving temperature str
# 9: decantation str
# 10: vintage num

# [need to be treated as bag of words]
# 11: style
# 12: charateristics

#[postprocessed results]
# 13: downloaded photo name
# 14: temperature min
# 15: temperature max
# 16: bag of words

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
        wine_tuple[11] = photo_filename
        
def _process_and_update_simple_text_fields(wine_tuple):
    for field_index in range(1, 5) + [7, 9, 10]:
        if wine_tuple[field_index]:
            wine_tuple[field_index] = wine_tuple[field_index].lower()

def _split_temperature_range2int(wine_tuple):
    temperature_range = wine_tuple[6]
    if not temperature_range: return
    new_range = re.findall(r'\d+', temperature_range)
    if not new_range:
        return 
    if len(new_range) > 2:
        new_range = new_range[:2]
    if len(new_range) < 2:
        new_range.append(new_range[0])
    wine_tuple[13], wine_tuple[14] = new_range[0], new_range[1]    

def _split_grapes2table(wine_tuple):
    grapes = wine_tuple[3]
    if not grapes: return
    wine_tuple[3] = [g.strip() for g in grapes.split(',')]
    
def _change_produced_year2vintage(wine_tuple):
    produced_year = wine_tuple[9]
    if not produced_year: return
    wine_tuple[9] = datetime.datetime.now().year - int(wine_tuple[9])

def _convert_alcohol2float(wine_tuple):
    alcohol_percent = wine_tuple[6]
    if not alcohol_percent: return
    alcohol_percent =  re.findall(r'\d+', alcohol_percent) 
    if not alcohol_percent: return
    wine_tuple[6] = alcohol_percent[0]

def _split_texts2bag_of_words(wine_tuple):
    text = (wine_tuple[10] or '') + (wine_tuple[11] or '')  
 
def _save2tnt(wine_tuple, tnt_connection):
    tnt_connection.call('wine.update_total', [wine_tuple, ])
               
def postprocess_wine(wine_tuple, tnt_connection):
    _download_and_save_photo(wine_tuple)
    _process_and_update_simple_text_fields(wine_tuple)
    _split_temperature_range2int(wine_tuple)
    _split_grapes2table(wine_tuple)
    _change_produced_year2vintage(wine_tuple)
    _convert_alcohol2float(wine_tuple)
    _split_texts2bag_of_words(wine_tuple)
    
    _save2tnt(wine_tuple, tnt_connection)
    
    
    
    

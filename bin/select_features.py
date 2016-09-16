import tarantool

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH

# wine space
# 1: name: str
# 2: image url: str
# 3: color: red/white/pink str
# 4: switness: dry/sweet/semi-sweet str
# 5: grape str
# 6. country str
# 7: region str
# 8: alcohol str --> float
# 9: serving temperature str
# 10: decantation str
# 11: vintage num

# [need to be treated as bag of words]
# 12: style
# 13: charateristics

#[postprocessed results]
# 14: downloaded photo name
# 15: temperature min
# 16: temperature max
# 17: bag of words

def extract_features_inplace(t, result_features_set, total_columns, ranges):
    name = t[0]
    print('processing document ' + name)
    
    if result_features_set.get(name): return
    
    result_features_set[name] = {
    }
    
    one_feature2order = {
        'color': 2,
        'switness': 3,
        'country': 5,
        'region': 6,
        'decantation': 9,
        'min_temperature': 16,
        'max_temperature': 17,
        'alcohol': 7,
        'vintage': 10,
        'ageing': 11 
        
    }
     
    for key, order in one_feature2order.items():
        if not t[order]: continue
        value = str(t[order])
        result_features_set[name][key + '_' + value] = 1
        total_columns.update([key + '_' + value, ])
        
        
    multiple_features2order = {
        'grape': 4
    }

    for key, order in multiple_features2order.items():
        if not t[order]: continue
        for value in t[order]:
            if not value: continue
            result_features_set[name][key + '_' + value] = 1
            total_columns.update([key + '_' + value, ])
            
    # words
    word_features2order = {
        'word_style__': 18,
        'word_characteristics__': 19,
        'word_gastronomy__': 20   
    }

    for key, order in word_features2order.items():
        if not t[order]: continue
        for word in t[order]:
            key += word
            if not result_features_set[name].get(key):
                result_features_set[name][key] =  0
            result_features_set[name][key] += 1
            total_columns.update([key, ])
            
    # TODO: ranges as ranges
    #result_features_set[name]['ranges'] = {
    #    'temperature': [t[14], t[15]],
    #    'alcohol': [t[7], ] * 2, #to unify process with ranges
    #    'vintage': [t[10], ] * 2, #to unify process with ranges
    #}         
    
    #for key, value in result_features_set[name]['ranges'].iteritems():
    #    ranges[key].update(value)

    # temperature range
    # alcohol range
    # vintage range

#def update_ranges(result_features_set, ranges):
#    for key in ranges.keys():
#       sorted(list(ranges)):
   
def _convert_hash2tuple(features_hash, total_columns):
    result = []
    for column in total_columns:
        curr_value = 0
        if features_hash.get(column):
            curr_value = features_hash.get(column)
        result.append(curr_value)
    return result
         
def save_docs_with_features(result_features_set, total_columns, tnt):
    total_columns = sorted(list(total_columns))
    for key in result_features_set.keys():
        print('saving document ' + key)
        tuple_ = _convert_hash2tuple(result_features_set[key], total_columns)
        tuple_ = [key, ] + tuple_
        try:
            tnt.call('feature.insert_feature', [[tuple_, ]])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass #its ok to loose some wines
    tnt.call('feature.insert_feature_names', [[total_columns, ], ])    
    
def collect_features():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    result_features_set = {}
    total_columns = set()
    ranges = {        
        'temperature': set(),
        'alcohol': set(),
        'vintage': set()
    }
    
    while len(tuples) > 0 and tuples[0]:
        for t in tuples:
            extract_features_inplace(t, result_features_set, total_columns, ranges)  
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data 
        
    #update_ranges(result_features_set, ranges)
    save_docs_with_features(result_features_set, total_columns, tnt)    

if __name__ == '__main__':
    collect_features()

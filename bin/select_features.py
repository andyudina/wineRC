import tarantool

from settings import TARANTOOL_CONNCTION

def extract_features_inplace(t, result_features_set, total_columns):
    raise NotImplemented
    
def save_docs_with_features(result_features_set, total_columns):
    raise NotImplemented
    
def collect_features():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    offset = 0
    tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data
    result_features_set = {}
    total_columns = {}
    while len(tuples) > 0 and tuples[0]:
        for t in tuples:
            extract_features_inplace(t, result_features_set, total_columns)  
        offset += CHUNK_LENGTH    
        tuples = tnt.call('wine.find_by_chunk', [offset, CHUNK_LENGTH, False ]).data 
        
   save_docs_with_features(result_features_set, total_columns)    


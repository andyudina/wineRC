import tarantool
from sklearn import preprocessing, feature_extraction
from sklearn.neighbors import NearestNeighbors
from scipy import sparse
import numpy

from settings import TARANTOOL_CONNCTION

def _find_non_word_feature(header):
    print(header)
    for i, name in enumerate(header):
        if name.startswith('word'):
            return i
    return len(header)
    
def _split2feature_types(features):
    header = features[0]
    body = features[1: ]
    
    # find non-word features number:
    non_word_feature_len = _find_non_word_feature(header)
    print(non_word_feature_len)
    
    np_body = numpy.array(body)
    return numpy.split(np_body, [1, non_word_feature_len], axis=1)
    
def _scale_count_features(features):
    preprocessing.scale(features, copy=False)
    
def _tfidf(features):
    tfidf = feature_extraction.text.TfidfTransformer()
    return tfidf.fit_transform(features)
    
def _merge_features(count_features, word_features):
    print(count_features.shape)
    print(word_features.shape)
    return sparse.hstack([count_features, word_features])
 
def _find_neighbours(x, y):
    nbrs = NearestNeighbors(n_neighbors=2, algorithm='ball_tree').fit(x)
    print(nbrs.kneighbors_graph(x).toarray())
     
def process_features():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    features = tnt.call('feature.get_feature_table', [[]]).data
    y, count_features, word_features = _split2feature_types(features)
    count_features = count_features.astype(float)
    word_features = word_features.astype(float)

    _scale_count_features(count_features)
    word_features = _tfidf(word_features)
    x = _merge_features(count_features, word_features)
    print(x)
    _find_neighbours(x, y)    

if __name__ == '__main__':
    process_features()

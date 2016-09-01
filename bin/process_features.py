import tarantool
from sklearn import preprocessing, feature_extraction, cluster, metrics, random_projection, decomposition
from sklearn.neighbors import NearestNeighbors
from scipy import sparse
import numpy

from settings import TARANTOOL_CONNCTION
NEIGHBOURS_TRESHOLD = 0.5

def _find_non_word_feature(header):
    for i, name in enumerate(header):
        if name.startswith('word'):
            return i
    return len(header)
    
def _split2feature_types(features):
    header = features[0]
    body = features[1: ]
    
    # find non-word features number:
    non_word_feature_len = _find_non_word_feature(header)
    
    np_body = numpy.array(body)
    return numpy.split(np_body, [1, non_word_feature_len], axis=1)
    
def _scale_count_features(features):
    preprocessing.scale(features, copy=False)
    
def _tfidf(features):
    tfidf = feature_extraction.text.TfidfTransformer()
    return tfidf.fit_transform(features)
    
def _merge_and_standardize_features(count_features, word_features):
    return preprocessing.StandardScaler(with_mean=False).fit_transform(sparse.hstack([count_features, word_features]))
 
def _find_neighbours(x, y):
    nbrs = NearestNeighbors(n_neighbors=2, algorithm='ball_tree').fit(x)
    neighbours = nbrs.kneighbors_graph(x).toarray()
    for i, _ in enumerate(neighbours):
        for j, _ in enumerate(neighbours[i]):
            if (neighbours[i][j] > NEIGHBOURS_TRESHOLD and i != j):
                print(i, '-', j, '-', neighbours[i][j]) 
                print(y[i], ' - ', y[j])

def _save_processed_features2tnt(y, x, tnt):
    y = y.tolist()
    x = x.toarray()
    for i, name in enumerate(y):
        tuple_ = list(name) + list(x[i])
        try:
            tnt.call('feature.insert_feature', [[tuple_, ], 'prepared_feature'])
        except tarantool.error.DatabaseError as e:
            print(e)
            pass #its ok to loose some wines

def _convert2dense(x):
    try:
        return x.toarray()
    except AttributeError:
        return x
        
def _evaluate_clustering(x, labels):
    try:
        return metrics.silhouette_score(x, labels, metric='euclidean')
    except ValueError: #too min labels
        return 0
   
def _test_cluster_algorithms(x, y):
    # KMeans/Agglomerative
    for n_clusters in range(2, 11):
        kmeans_model = cluster.KMeans(n_clusters=n_clusters).fit(x)
        print('kmeans accuracy for # clusters{}: {}'.format(n_clusters, _evaluate_clustering(x, kmeans_model.labels_)))
        agglomerationg_model = cluster.AgglomerativeClustering(n_clusters=n_clusters).fit(_convert2dense(x))
        print('agglomerationg accuracy for # clusters{}: {}'.format(
            n_clusters, 
            _evaluate_clustering(x, agglomerationg_model.labels_)))
        
    # AffinityPropagation 
    for dumping_factor in range(5, 10):
        dumping_factor = float(dumping_factor) / 10
        model = cluster.AffinityPropagation(damping=dumping_factor).fit(x)
        print('affinity propagation accuracy for dumping: {} == {}'.format(
            dumping_factor,  
            _evaluate_clustering(x, model.labels_)))
            
    #MeanShift
    model = cluster.MeanShift().fit(_convert2dense(x))
    print('meanshoft accuracy for dumping: {}'.format(
           _evaluate_clustering(x, model.labels_)))
     
    #DBSCAN
    for eps in range(1, 5):
        eps = float(eps) / 10
        for min_samples in range(5, 20):
            model = cluster.DBSCAN(eps=eps).fit(x)
            n_clusters_ = len(set(model.labels_)) - (1 if -1 in model.labels_ else 0)
            print('dbscan N clusters: {} for min_samples = {}'.format(n_clusters_, min_samples))
            print('dbscan accuracy for eps: {} and min_samples == {}'.format(
                eps,  
                min_samples,
                _evaluate_clustering(x, model.labels_)))
            
    #Birch
    for threshold in range(1, 7):
        threshold = float(threshold) / 10
        model = cluster.Birch(threshold=threshold).fit(x)
        
        print('birch accuracy for threshold: {} == {}'.format(
            threshold,  
            _evaluate_clustering(x, model.labels_)))

def _test_feature_extraction_algorithms(x, y):
    feature_selectors = {
        'PCA': decomposition.PCA(),
        'SparseRandomProjection': random_projection.SparseRandomProjection(eps=0.35),
        'GaussianRandomProjection': random_projection.GaussianRandomProjection(eps=0.35),
    }  
    for n_clusters in range(2, 10):
        feature_selectors['FeatureAgglomeration: {}'.format(n_clusters)] = cluster.FeatureAgglomeration(n_clusters=n_clusters)  
        
    for name, selector in feature_selectors.items():
        x_new = selector.fit_transform(x.toarray())
        print('\n\n FEATURES SELECTED WITH: {}'.format(name))
        _test_cluster_algorithms(x_new, y)
                          
def process_features():
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)
    features = tnt.call('feature.get_feature_table', [[]]).data
    y, count_features, word_features = _split2feature_types(features)
    count_features = count_features.astype(float)
    word_features = word_features.astype(float)

    _scale_count_features(count_features)
    word_features = _tfidf(word_features)
    x = _merge_and_standardize_features(count_features, word_features)
    #_save_processed_features2tnt(y, x, tnt)
    
    #_test_cluster_algorithms(x, y)
    
    #_test_feature_extraction_algorithms(x, y) --> 4, 5, 6, 7 by Feauture agglomeration
    #_find_neighbours(x, y)    

if __name__ == '__main__':
    process_features()

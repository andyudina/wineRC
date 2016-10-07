# Здесь логика хранения

from itertools import product, chain

import tarantool
import networkx as nx
import numpy as np

from lib.models.base import Base

class Session(Base):
    fields = [
        'id',
        'created_at', 
        'color',
        'sweetness',
        'country', 
        'vintage', 
        'aging',
        'styling',
        'current_question',
        'wine_names',
        'yes_categories',
        'no_categories',
        'graph',
        
        'features_x',
        'features_y',
        'current_relative_nodes',
        'answered_questions_number',
        
        'results'
    ]

    formal_features = [
        'color',
        'sweetness',
        'country', 
        'vintage', 
        'aging',
        'styling',
    ]
        
    _fields4deserialize = [
        'graph',
        'features_x',
        'features_y',
        'yes_categories',
        'no_categories'
    ]
    
    @classmethod
    def get_session(cls, user_id):
        t = cls.tnt.call('session.get_session', [user_id, ]).data[0]
        session = Session(**cls.tuple2hash(t))
        session._deserialize_inplace()
        #session.graph = session._deserialize_graph()
        return session
    
    def __init__(self, *args, **kwargs):
        super(Session, self).__init__(*args, **kwargs)
        #self._updated_fields = {}
        #self._fields_dict = {key: 1 for key in self.fields}
     
    #def __setattr__(self, name, value):
    #    if self._fields_dict.get(name):
    #        self._updated_fields[name] = 1
    #    super(Session, self).__setattr__(name, value)
         
    def _deserialize_inplace(self):
        for field in self._fields4deserialize:
            getattr(self, '_deserialize_{}'.format(field))()
                 
    def update(self, **kwargs): 
        fields2update = self.fields #list(self._updated_fields.values())
        if kwargs.get('fields'):
            fields2update = kwargs.get('fields') 
        if not fields2update:
            return
        values2update = [ 
            [ i + 1, self.serialize(field) ] \
            for i, field in enumerate(self.fields) if field in fields2update
        ]
        try:
            self.tnt.call('session.update_local', [self.id, list(chain.from_iterable(values2update))])
            #print([self.id, values2update])
            
        except tarantool.error.DatabaseError as e:
            print(e)
 
    ## serialization
            
    def serialize(self, field):
        if hasattr(self, '_serialize_{}'.format(field)):
            return getattr(self, '_serialize_{}'.format(field))()
        return getattr(self, field)  
          
    def _deserialize_graph(self):
        #print(self.__dict__)  
        nodes, edges = self.graph
        self.graph = nx.MultiGraph(name="words")
        self.graph.add_nodes_from(nodes)
        self.graph.add_edges_from(edges)
        return self.graph
        
    def _serialize_graph(self):
        return [self.graph.nodes(), self.graph.edges()]
 
    def _deserialize_features_x(self):  
        self.features_x = np.array(self.features_x)
        return self.features_x
        
    def _serialize_features_x(self):
        return self.features_x.tolist()

    def _deserialize_features_y(self):  
        self.features_y = np.array(self.features_y)
        return self.features_y
        
    def _serialize_features_y(self):
        return self.features_y.tolist()       

    def _deserialize_yes_categories(self):  
        self.yes_categories = {key: 1 for key in self.yes_categories}
        return self.yes_categories
        
    def _serialize_yes_categories(self):
        return list(self.yes_categories.keys())

    def _deserialize_no_categories(self):  
        self.no_categories = {key: 1 for key in self.no_categories}
        return self.no_categories
        
    def _serialize_no_categories(self):
        return list(self.no_categories.keys())
    
    ## formal features                              
    def get_formal_features(self):
        return [getattr(self, attr) for attr in self.formal_features]
        
    def get_next_not_answered_formal_feature(self):
        for feature in self.formal_features:
            if getattr(self, feature) is None: return feature
        return None   
        
    def update_formal_feature(self, key, value): 
        #print(key)
        #print(value)
        setattr(self, key, value)
        #print(getattr(self, key))
        

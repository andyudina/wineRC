import tarantool

from settings import TARANTOOL_CONNCTION, CHUNK_LENGTH

class Base:
    tnt = tarantool.connect(**TARANTOOL_CONNCTION)  
    
    @classmethod
    def get_by_chunks(cls, method_name, *extra_call_args):
        offset = 0
        tuples = cls.tnt.call(method_name, [offset, CHUNK_LENGTH, ] + list(extra_call_args)).data
    
        result_tuples = []
        while len(tuples) > 0 and tuples[0]:
            result_tuples.extend(tuples)
            offset += CHUNK_LENGTH    
            tuples = cls.tnt.call(method_name, [offset, CHUNK_LENGTH, ] + list(extra_call_args)).data
        return result_tuples  
       
    @classmethod
    def tuple2hash(cls, t):
        res = {}
        #if len(cls.fields) != len(t):
        #    print(t)
        #    print(cls.fields)
        for index, value in enumerate(t):
            res[cls.fields[index]] = value
        return res
       
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
                

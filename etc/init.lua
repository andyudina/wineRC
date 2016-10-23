
box.cfg {
    listen = 3311,
    logger = 'tarantool.log',
    slab_alloc_maximal = 6291456 
} 

wine     = require 'wine'
catalog  = require 'catalog'
feature  = require 'feature'
synonyms = require 'synonyms'
question = require 'question'
session  = require 'session'

box.schema.user.create('root', {if_not_exists = true, password='1234'})
box.schema.user.grant('root', 'drop,alter,create,read,write,execute', 'universe', nil, {if_not_exists = true})
--for _, func_name in pairs({'insert_local', 'insert', 'delete_by_page', 'delete_by_pk'}) do
--    box.schema.user.grant('root', 'execute', 'function', func_name)
--end



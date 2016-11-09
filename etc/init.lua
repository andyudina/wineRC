
box.cfg {
    listen = 3311,
    logger = 'tarantool.log',
    --slab_alloc_arena = 0.05,
    --slab_alloc_maximal = 1459392
    slab_alloc_maximal = 3145728
} 

wine     = require 'wine'
catalog  = require 'catalog'
feature  = require 'feature'
synonyms = require 'synonyms'
question = require 'question'
session  = require 'session'

box.schema.user.create('root', {if_not_exists = true, password='1234'})
box.schema.user.grant('root', 'drop,alter,create,read,write,execute', 'universe', nil, {if_not_exists = true})



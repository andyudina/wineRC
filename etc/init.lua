
box.cfg {
    listen = 3311,
    logger = 'tarantool.log',
} 

wine = require 'wine'
catalog = require 'catalog'

box.schema.user.create('root', {if_not_exists = true, password='1234'})
box.schema.user.grant('root', 'read,write,execute', 'universe')
--for _, func_name in pairs({'insert_local', 'insert', 'delete_by_page', 'delete_by_pk'}) do
--    box.schema.user.grant('root', 'execute', 'function', func_name)
--end



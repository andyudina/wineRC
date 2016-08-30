catalog = box.schema.space.catalog
if not catalog then
    catalog = box.schema.space.create('catalog')
    catalog_primary = catalog:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: url: str
-- 2: page: number

local function insert(args) 
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        catalog:insert(tuple)
    end
end

local function delete_by_pk(...)
    local args = {...}
    if #args == 0 then
        return
    end
    for _, pk in pairs(args) do
        catalog:delete(pk)
    end
end

return {
    delete_by_pk = delete_by_pk,
    insert = insert
}

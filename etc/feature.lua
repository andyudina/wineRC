feature = box.space.feature
if not feature then
    feature = box.schema.space.create('feature')
    feature_primary = feature:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: name: str
-- 2: features ...

feature_name = box.space.feature_name
if not feature_name then
    feature_name = box.schema.space.create('feature_name')
    feature_name_primary = feature_name:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: name: str

prepared_feature = box.space.prepared_feature
if not prepared_feature then
    prepared_feature = box.schema.space.create('prepared_feature')
    prepared_feature_primary = prepared_feature:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: name: str
-- 2: features ...

local function insert_feature(args, space)
    if #args == 0 then
        return
    end
    if space == nil then
        space = 'feature' -- for backwords compability
    end
    for _, tuple in pairs(args) do
        box.space[space]:replace(tuple)
    end
end

local function delete(name)
    box.space.feature:delete{name}
end

local function find_by_chunk(offset, chunk_length)
    offset = tonumber(offset)
    chunk_length = tonumber(chunk_length)

    local curr_length = 0
    local res_table = {}


    for _, tuple in box.space.feature.index.primary:pairs({iterator = box.index.ALL}) do
        if curr_length >= chunk_length + offset then
            break
        end

        if curr_length >= offset then
            table.insert(res_table, tuple)
        end
        curr_length = curr_length + 1
    end
    return res_table
end


local function insert_feature_names(args)
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        box.space['feature_name']:insert(tuple)
    end
end

local function replace_feature_names(args)
    if #args == 0 then
        return
    end
    for _, tuple in box.space['feature_name'].index.primary:pairs({iterator = box.index.ALL}) do
        box.space['feature_name']:delete{tuple[1]}
    end

    for _, tuple in pairs(args) do
        box.space['feature_name']:insert(tuple)
    end
end

local function get_feature_table()
    local header = {'name'}
    for _, tuple in box.space['feature_name'].index.primary:pairs({iterator = box.index.ALL}) do
        for _, name in pairs({tuple:unpack()}) do
            table.insert(header, name)
        end
    end

    result = {header, }
    for _, tuple in box.space['feature'].index.primary:pairs({iterator = box.index.ALL}) do
        table.insert(result, tuple)
    end
    return result
end

local function get_feature_names()
    local header = {}
    for _, tuple in box.space['feature_name'].index.primary:pairs({iterator = box.index.ALL}) do
        for _, name in pairs({tuple:unpack()}) do
            table.insert(header, name)
        end
    end
    return header
end

local function get_features()
    result = {}
    for _, tuple in box.space['feature'].index.primary:pairs({iterator = box.index.ALL}) do
        table.insert(result, tuple)
    end
    return result
end

return {
    insert_feature_names = insert_feature_names, 
    insert_feature = insert_feature,
    get_feature_table = get_feature_table,
    replace_feature_names = replace_feature_names,
    get_feature_names = get_feature_names,
    get_features = get_features,
    delete = delete,
    find_by_chunk = find_by_chunk,
}

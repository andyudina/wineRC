wine_schema = box.space['wine']
if  wine_schema == nil then
    wine_schema = box.schema.space.create('wine')
    wine_primary = wine_schema:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: name: str
-- 2: color: red/white/pink str
-- 3: switness: dry/sweet/semi-sweet str
-- 4: grape str
-- 5: country str
-- 6: region str
-- 7: alcohol str --> num
-- 8: serving temperature str
-- 9: decantation str
-- 10: vintage num

-- [need to be treated as bag of words]
-- 11: style
-- 12: charateristics

--[postprocessed results]
-- 13: downloaded photo name
-- 14: temperature min
-- 15 temperature max
-- 16: bag ow words

local MAX_TUPLE_LENGTH = 17
local function insert_local(...) 
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        for i = #tuple + 1, MAX_TUPLE_LENGTH do
            table.insert(tuple, nil) -- fill tuple with nulls
        end
        wine_schema:insert(tuple)
    end
end

local function update_local(...)
    -- expected format:
    -- pk_1, {place_in_tuple_1, new_value_1, ...}, 

    local args = {...}
    if #args == 0 then
        return
    end
    for i = 1, #args, 2 do
        pk = args[i]
        tuple4update = args[i + 1]
        local table4update = {}
        for j = 1, #tuple4update do
            table.insert(table4update, {'=', tuple4update[j], tuple4update[j + 1]})
        end
        box.space.wine:update(pk, table4update)
    end
end
    

local function update_total(...)
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        pk = tuple[1]
        local table4update = {}
        for j = 2, #tuple do
            if tuple[j] then
                table.insert(table4update, {'=', j, tuple[j]})
            end
        end
        box.space.wine:update(pk, table4update)
    end
end

local function find_by_chunk(offset, chunk_length, only_new)
    offset = tonumber(offset)
    chunk_length = tonumber(chunk_length)

    local curr_length = 0
    local res_table = {}
    for _, tuple in box.space.wine.index.primary:pairs({iterator = box.index.ALL}) do
        if curr_length >= chunk_length then
            break
        end

        if curr_length >= offset and 
           (not only_new or tuple[14] == nil) then -- check if tuple was not post processed yet (and image is empty)
            table.insert(res_table, tuple)
            curr_length = curr_length + 1
        end
    end
    return res_table
end

local function delete_by_pk(pk)
    box.space.wine:delete(tostring(pk))
end

return {
    find_by_chunk = find_by_chunk,
    update_local = update_local,
    update_total = update_total,
    insert_local = insert_local,
    delete_by_pk = delete_by_pk,
}

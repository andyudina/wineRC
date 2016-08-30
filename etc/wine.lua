wine_schema = box.schema.space.wine
if not wine_schema then
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

local function insert_local(...) 
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        for i = #tuple + 1, 16 do
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

return {
    update_total = update_total,
    update_local = update_local,
    insert_local = insert_local
}

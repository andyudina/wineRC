question_schema = box.space['question']
if  question_schema == nil then
    question_schema = box.schema.space.create('question')
    question_primary = question_schema:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: category: str
-- 2: questions: arr

local function insert_local(...) 
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        question_schema:insert(tuple)
    end
end

local function replace_local(...)
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        question_schema:replace(tuple)
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
        for j = 1, #tuple4update, 2 do
            table.insert(table4update, {'=', tuple4update[j], tuple4update[j + 1]})
        end
        box.space.question:update(pk, table4update)
    end
end

local function find_all()
    local res_table = {}
    for _, tuple in box.space.question.index.primary:pairs({iterator = box.index.ALL}) do
        table.insert(res_table, tuple)
    end
    return res_table
end

local function delete_by_pk(pk)
    box.space.question:delete(tostring(pk))
end

local function find_by_chunk(offset, chunk_length)
    offset = tonumber(offset)
    chunk_length = tonumber(chunk_length)

    local curr_length = 0
    local res_table = {}
    for _, tuple in box.space.question.index.primary:pairs({iterator = box.index.ALL}) do
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

return {
    find_by_chunk = find_by_chunk,
    find_all = find_all,
    update_local = update_local,
    insert_local = insert_local,
    replace_local = replace_local,
    delete_by_pk = delete_by_pk,
}

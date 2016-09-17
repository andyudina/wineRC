synonym_schema = box.space['synonym']
if  synonym_schema == nil then
    synonym_schema = box.schema.space.create('synonym')
    synonym_primary = synonym_schema:create_index('primary', {type = 'tree', parts = {1, 'STR'}})
end
-- 1: name: str
-- 2: synonyms arr

local function upsert_local(...) 
    local args = {...}
    if #args == 0 then
        return
    end
    for _, tuple in pairs(args) do
        synonym_schema:upsert(tuple, {{'=', 2, tuple[2]}})
    end
end


local function find_by_chunk(offset, chunk_length)
    offset = tonumber(offset)
    chunk_length = tonumber(chunk_length)

    local curr_length = 0
    local res_table = {}
    for _, tuple in box.space.synonym.index.primary:pairs({iterator = box.index.ALL}) do
        if curr_length >= chunk_length then
            break
        end

        if curr_length >= offset then
            table.insert(res_table, tuple)
            curr_length = curr_length + 1
        end
    end
    return res_table
end

local function delete_by_pk(pk)
    box.space.synonym:delete(tostring(pk))
end

return {
    find_by_chunk = find_by_chunk,
    upsert_local = upsert_local,
    delete_by_pk = delete_by_pk,
}

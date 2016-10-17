session_schema = box.space['session']
if  session_schema == nil then
    session_schema = box.schema.space.create('session')
    session_schema:create_index('primary', {type = 'tree', parts = {1, 'NUM'}})
    session_schema:create_index('created_at', {type = 'tree', parts = {1, 'NUM'}})
end

-- 1: id: NUM, 
-- 2: created_at: number, 

-- formal features
-- 3: color: string,
-- 4: sweetness: string,
-- 5: country: string, 
-- 6: vintage: string, 
-- 7: aging: number (1 да, 2 нет 0 пофиг):
-- 8: styling: array

-- 9: current_question
-- 10: wine_names ARR --wines selected by formal features

-- taste features
-- 11: yes_categories
-- 12: no_categories
-- 13: graph: { {'node1', 'node2', 'node3'}, {{'node1', 'node2'}, {'node2', 'node3'}} }
-- 14: features_x: {}
-- 15: features_y: {}
-- 16: current_relative_nodes: {},
-- 17: answered_questions_number NUM
-- 18: results: {}

local function start_session(user_id) 
    local session = {
        user_id,
        os.time(),
        
        nil,
        0,
        0,  --TODO: create questions and remove preselected values
        0,  --TODO
        0,
        {}, --TODO
        
        nil,
        {},
        
        {},
        {},
        {{}, {}},
        {},
        {},
        {},
        0,
        {}
    }
    session_schema:replace(session)
    return session
end

local function close_session(user_id)
    session_schema:delete{user_id}
end

local function get_session(user_id)
    local session = session_schema:get{user_id}
    if session == nil then
        session = start_session(user_id)
    end
    return session
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
        box.space.session:update(pk, table4update)
    end
end

local function find_session(user_id)
    return box.space.session:get{user_id}
end

local TWO_MONTHS = 2 * 30 * 24 * 3600
local function close_old_sessions(pk)
    local ts_treshold = os.time() - TWO_MONTHS
    for _, t in box.space.session.index.created_at:pairs(ts_treshold, {iterator=box.index.LTE}) do
        box.space.session:delete(t[1])
    end
end

return {
    get_session = get_session,
    find_session = find_session,
    close_old_sessions = close_old_sessions,
    update_local = update_local,
    start_session = start_session,
    close_session = close_session
}

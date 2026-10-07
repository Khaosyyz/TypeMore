-- typemore 引擎侧:语境加权过滤 + 学习清单落库 + 选词转发
-- 三个通道文件均在引擎用户目录;侧车原子写,本侧只读/追加
local M = {}

local function read_lines(path)
    local f = io.open(path, "r")
    local lines = {}
    if f then
        for line in f:lines() do
            if #line > 0 then
                table.insert(lines, line)
            end
        end
        f:close()
    end
    return lines
end

function M.init(env)
    env.dir = rime_api.get_user_data_dir()
    local config = env.engine.schema.config
    env.boost_scan = config:get_int("typemore/boost_scan") or 50
    env.learn_commits = config:get_int("typemore/learn_commits") or 100
    env.mem = Memory(env.engine, env.engine.schema)
    env.learn_seq = 0
    env.last_input = ""
    env.select_notifier = env.engine.context.select_notifier:connect(function(ctx)
        env.last_input = ctx.input
    end)
    env.commit_notifier = env.engine.context.commit_notifier:connect(function(ctx)
        local text = ctx:get_commit_text()
        if text and #text > 0 then
            local f = io.open(env.dir .. "/typemore_feed.log", "a")
            if f then
                f:write(text .. "\t" .. env.last_input .. "\n")
                f:close()
            end
        end
        env.last_input = ""
    end)
end

function M.fini(env)
    env.select_notifier:disconnect()
    env.commit_notifier:disconnect()
end

local function apply_learn(env)
    local lines = read_lines(env.dir .. "/typemore_learn.txt")
    local seq = tonumber(lines[1])
    if not seq or seq <= env.learn_seq then
        return
    end
    env.learn_seq = seq
    for i = 2, #lines do
        local w, py = lines[i]:match("^(%S+)%s+([a-z ]+)$")
        if w and py then
            local e = DictEntry()
            e.text = w
            e.custom_code = py .. " "
            if env.mem.start_session then
                env.mem:start_session()
            end
            env.mem:update_userdict(e, env.learn_commits, "")
            if env.mem.finish_session then
                env.mem:finish_session()
            end
            log.info("[typemore] learned: " .. w .. " <- " .. py)
        end
    end
end

local function read_boost(env)
    local boost = {}
    local lines = read_lines(env.dir .. "/typemore_boost.txt")
    for _, line in ipairs(lines) do
        local w, s = line:match("^(%C+)%s+([%d%.]+)$")
        if w then
            boost[w] = tonumber(s)
        end
    end
    return boost
end

-- 过滤阶段改 quality 不重排;取前 boost_scan 个候选按加分重排后先行 yield
function M.func(translation, env)
    env.last_input = env.engine.context.input or env.last_input
    apply_learn(env)
    local boost = read_boost(env)
    local head, n = {}, 0
    for cand in translation:iter() do
        if n < env.boost_scan then
            n = n + 1
            head[n] = { cand = cand, score = boost[cand.text] or 0, idx = n }
        else
            break
        end
    end
    table.sort(head, function(a, b)
        if a.score ~= b.score then
            return a.score > b.score
        end
        return a.idx < b.idx
    end)
    for _, item in ipairs(head) do
        yield(item.cand)
    end
    for cand in translation:iter() do
        yield(cand)
    end
end

return M

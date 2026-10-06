-- typemore 引擎侧:语境加权过滤 + 学习清单落库 + 选词转发
-- 三个通道文件均在 rime 用户目录,侧车原子写入(os.replace),引擎侧只读/追加
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
        local w, py = lines[i]:match("^(%C+)%s+([a-z ]+)$")
        if w and py then
            local e = DictEntry()
            e.text = w
            e.custom_code = py .. " "
            if env.mem.start_session then
                env.mem:start_session()
            end
            env.mem:update_userdict(e, 1, "")
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

function M.func(translation, env)
    apply_learn(env)
    local boost = read_boost(env)
    for cand in translation:iter() do
        local b = boost[cand.text]
        if b and b > 0 then
            cand.quality = cand.quality + b
        end
        yield(cand)
    end
end

return M

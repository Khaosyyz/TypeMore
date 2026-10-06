# typemore

缓冲区式拼音输入法:所有输入先进缓冲区,本地引擎实时给候选(跟手、纯查表);云端大模型按周期矫正缓冲区文本,并把矫正结果以"别词学习"反哺本地候选权重;双击空格,缓冲区文本一次性上屏。

## 原则

- 产品开源(GPL-3 兼容路线)。
- **现成的、产品化的代码和方法直接用**;只有市面上不存在的东西才自己写。
- 用户只装 typemore 一个东西:引擎、词库、模型全部随产品分发,不依赖用户预装任何输入法。
- 每个文件都必须有存在的理由,不留孤立代码。

## 组装关系(谁干什么)

| 层 | 用什么 | 来源 | 我们的动作 |
|---|---|---|---|
| 引擎 | librime(BSD) | 开源引擎,随产品分发 | 直接用;要动刀时改源码或走 Lua 正门 |
| 词库 | 雾凇(GPL-3,已确认开源路线) | iDvel/rime-ice | 原文件直接用 |
| 语境打分(n-gram) | octagram 插件(BSD)+ .gram 数据(LGPL-3) | lotem/librime-octagram(-data) | 已激活(`rime/rime_ice.custom.yaml`) |
| 用户词典调频 | librime userdb | 引擎自带 | 直接用;别词学习的写入目标 |
| 语境加权 | Lua 过滤器 | — | **待开发**:眼前账/会话账加分 |
| 云端矫正 + 别词学习 | 我们的服务 | — | **待开发**:每 10 字矫正,diff→词级配对→回写 userdb |
| 缓冲区 + 双空格交互 | 我们的界面 | — | **待开发**:先简后美,最终走 TSF 接入系统 |
| 开发期测试台 | 小狼毫 Weasel(GPL-3) | 已装在本机 | 仅开发用,不进产品 |

## 结构

```
typemore/
├── rime/                    # 部署配置层(单一事实来源,部署 = 拷入 Rime 用户目录)
│   ├── *.yaml, cn_dicts/, en_dicts/, lua/, opencc/   # 雾凇方案原文件
│   ├── grammar.yaml                    # octagram 语法配置
│   ├── zh-hans-t-essay-bgw.gram        # n-gram 模型(41MB)
│   └── rime_ice.custom.yaml            # ★ 我们的自有配置:激活语法模型
└── README.md
```

部署:停 WeaselServer/WeaselDeployer → 清空 `%APPDATA%\Rime` → 拷入 `rime/*` → `WeaselDeployer.exe /deploy`(注意:参数须经 powershell/python 传递,MSYS 会误转换;服务器运行中部署会卡死)→ 重启 WeaselServer。

## 进度

- [x] 组件选型 + 协议核查(BSD/LGPL/GPL 组合,产品开源路线下全部合规)
- [x] 雾凇方案部署可用(55 万+词库,1.93M 全量可选)
- [x] octagram 语法模型激活并验证生效(编译产物含 grammar,部署日志 resolved Include(grammar:/hans))
- [x] 部署流程自动化知识沉淀(见上)
- [ ] 语境加权 Lua 过滤器(眼前账/会话账加分进候选)
- [ ] 云端矫正服务(每 10 字)
- [ ] 别词学习(矫正 diff → 同拼音词对 → 回写 userdb)
- [ ] 缓冲区界面 + 双空格(自有前端,先简后美,TSF 接入)

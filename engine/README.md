# typemore 引擎模块

本目录是 typemore 的传统输入法引擎:拼音切分 → 词典检索 → 候选打分排序 → 用户词典(userdb)。
源自 librime,以 BSD-3 许可吸收进本项目,以下保留各源码的原始许可与版本出处。

## 源码出处(吸收时版本)

| 组件 | 上游 | 版本 | 许可 |
|---|---|---|---|
| 核心引擎 | github.com/rime/librime | 7bc3fb0 (2026-10-01) | BSD-3(见 LICENSE) |
| Lua 扩展 | github.com/hchunhui/librime-lua | 6f30968 (2026-09-30) | BSD-3(见 plugins/lua/LICENSE) |
| 八股文语法 | github.com/lotem/librime-octagram | 57d18b9 (2026-08-31) | BSD-3(见 plugins/octagram/LICENSE) |
| glog | github.com/google/glog | 7b134a5 | 上游许可 |
| googletest | github.com/google/googletest | f8d7d77 | 上游许可 |
| leveldb | github.com/google/leveldb | 99b3c03 | 上游许可 |
| marisa-trie | github.com/s-yata/marisa-trie | 3e87d53 | 上游许可 |
| OpenCC | github.com/BYVoid/OpenCC | 025f371 | 上游许可 |
| yaml-cpp | github.com/jbeder/yaml-cpp | 2f86d137 | 上游许可 |

依赖版本与 librime 上游 submodule 指针一致。

## 吸收时的裁剪

删除:.git/.github(CI)、Dockerfile、CI 辅助脚本(action-*)、版本工具
(bump-version.sh、cliff.toml、rime-new-plugin.sh)、sample/、上游 README 与
CHANGELOG(出处已记录于本文件)。其余未改动。

## 修改记录

- 吸收时未做任何代码修改。
- 后续对上游代码的修改在此登记:修改目的 + 涉及文件。

## 构建方式

Windows:build.bat(需 MSVC + CMake,依赖见 deps.mk;boost 用 install-boost.bat 获取)。
构建产物为引擎库,由 typemore 前端加载,随 typemore 产品分发。

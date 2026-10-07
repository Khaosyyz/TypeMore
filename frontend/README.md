# typemore 前端:TSF 文本服务(生产形态)

Python 原型(lab/prototype_ime.py)验证了全部交互逻辑;生产形态是注册进系统的 TSF 输入法,
按键由系统按焦点路由到我们——无需全局钩子、无需手动开关、光标位置由 TSF 精确给出。
本文件是 C++ 构建前的定案。

## 生产架构(三个常驻部分)

```
┌─ 前端 TSF DLL(frontend/,C++)────────────────┐
│ 注册为系统输入法;按键按焦点进入                 │
│ 进程内加载 rime.dll(引擎 C API,非 Lua 通道)   │
│ 候选窗/缓冲区行:UILess 模式(ITfUIElement)     │
│ 组合转换:ITfComposition,提交走 setText         │
├─ 后台服务(main.py,现成)──────────────────┤
│ feed→缓冲区→云端矫正→学习→boost/learn 通道     │
├─ 引擎(rime.dll,现成)+ 数据(rime/,现成)───┤
│ 雾凇词典 + octagram + lua(boost/learn/feed)    │
└──────────────────────────────────────────┘
```

三通道文件(.typemore_boost/learn/feed)原样保留——TSF DLL 与 Python 服务经同一目录协作,
用户目录 = 安装目录/runtime/rime-user。

## TSF DLL 需要实现的接口(阶段清单)

1. COM 自注册:DllRegisterServer/DllUnregisterServer(CLSID + 键盘布局 + 语言配置文件,regsvr32)
2. ITfTextInputProcessorEx:Activate/Deactivate——Activate 时建 rime 会话、挂按键 sink
3. ITfKeyEventSink:键规则与 Python 原型一致(字母/数字/标点进引擎,空格三态,退格三态,
   配置读 config.yaml [hotkeys]);修饰键组合直通由"不消费"天然实现,无卡键问题
4. ITfComposition + ITfContextEdit:转换中在应用内显示预编辑(拼音),
   空格/数字上屏 → 终止组合写文本;缓冲区文本经 SendInput 或 ITfRange::SetText 注入
5. 候选窗:ITfUIElementCandidateList(UILess)承载候选行+缓冲区行,位置
   ITfContextView::GetTextExt 精确锚定光标(原型的 GetGUIThreadInfo 是它的降级模拟)
6. 消费 config.yaml:自写极简 YAML 读取或编译期嵌入默认值(避免引入 yaml-cpp 依赖)

## 构建与部署

- 工具链:VS2022 BuildTools + Windows SDK 10.0.22621(均已装,msctf.h 在 SDK 内)+ CMake(pip 版)
- frontend/CMakeLists.txt → typemore_tsf.dll;部署 = regsvr32 注册 + 文件落安装目录
- 卸载 = regsvr32 /u;系统输入法列表中按用户选择启用(生产形态的"开关")

## 分阶段里程碑

- 阶段1:空服务注册成功,任务栏出现"typemore",键事件可达(日志验证)
- 阶段2:进程内接 rime.dll,预编辑+候选数据就绪
- 阶段3:UILess 候选窗(候选行+缓冲区行),组合提交全流程
- 阶段4:与后台服务联调(矫正改写缓冲区、学习回写 userdb)

风险备忘:UILess 在部分应用受限(需回退自绘窗口);管理员权限窗口需 same-integrity;
防密码框窃取:检测输入场景显示密码属性时禁用缓冲区行(阶段3 加入)。

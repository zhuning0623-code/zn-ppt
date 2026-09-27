# zn-ppt

面向 Codex 的 PPT 制作技能：先规划、再制作，强调具体内容、原创排版、真实 AI 配图、可编辑对象与原生动态效果。

## 功能

- 先给出可修改的逐页内容与视觉方案，确认后制作。
- 按主题设计不同构图，避免整套重复固定模板。
- 实际调用可用的 ImageGen，生成与内容相关的图片。
- 文字、表格、数据图表与流程图使用原生可编辑对象。
- 为 PPTX 写入淡化、推进、擦除等转场，并按点击分步出现。
- 交付 PPTX 与整套静态预览，明确结构检查和实播检查的区别。

## 安装

下载本仓库，将包含 `SKILL.md` 的目录命名为 `zn-ppt`，放入你的 Codex 技能目录（通常为 `~/.codex/skills/zn-ppt`）。重新打开会话后调用 `$zn-ppt`。

## 使用示例

```text
用 $zn-ppt 制作一套关于人工智能应用的 14 页中文 PPT。
听众为非技术人员，演讲约 15 分钟。
先给我逐页内容、视觉方向和动效计划，确认后制作。
要求有具体案例、真实 AI 配图和可编辑图表。
```

已有方案时可直接说：“按已确认方案用 zn-ppt 制作。”

## 运行条件与边界

此仓库包含技能指令和动效辅助脚本，不包含模型服务、API 密钥、商业软件或独立 PPT 渲染引擎。

完整流程需要宿主环境提供 ImageGen，以及 presentations 演示制作技能及其运行时。辅助脚本使用 Python 3 和 `lxml`；缺少时可在合适的 Python 环境安装 `lxml`。

生成图片为独立位图，可以替换或裁切，图内像素不能逐项编辑。具体生图模型取决于宿主环境；本技能不保证或强制某个模型版本。

动效脚本支持基础原生转场和点击出现，不支持 Morph 或复杂路径动画。PowerPoint、WPS 和 Google Slides 的兼容性可能不同；结构检查不代表已完成实播放映验证。静态预览不展示动态效果。

## 文件结构

- `SKILL.md`：工作流入口
- `agents/openai.yaml`：技能展示信息
- `references/`：内容、视觉、生图、动效与交付要求
- `scripts/pptx_motion.py`：PPTX 动效写入与检查

## 动效工具

```sh
python3 scripts/pptx_motion.py inspect draft.pptx
python3 scripts/pptx_motion.py apply draft.pptx --plan motion.json --output final.pptx
python3 scripts/pptx_motion.py inspect final.pptx --require-images --require-transitions --require-reveals
```

动效计划格式和对象选择方法见 [动态效果实现](references/transitions.md)。

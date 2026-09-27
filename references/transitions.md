# 动态效果实现

## 先设计，再写入

页间转场与页内动画分别处理。完整多页 PPTX 默认在非封面页写入转场，并在过程、案例揭示或分层解释页设置点击出现。普通页面平稳切换，阶段推进或章节转折可使用更明显的推进或擦除；不要全稿只靠不易察觉的淡化表达“有特效”。强度服从主题和用户要求，不随机堆叠。

页内动画按讲述顺序揭示有意义的内容组，标题与阅读上下文通常先保持可见。不要让读者每看一个字都点击，不自动播放、不加声音，除非用户要求。短稿至少选择一个适合的内容页；中长稿在多个关键页面安排，不把装饰闪动当作解释动画。

## 随附工具

使用工作区演示 Python 运行时（含 lxml），定位本 skill 的 scripts/pptx_motion.py。工具操作新的输出文件，原文件保留。它支持 fade、push、wipe、cut 转场，以及原生按点击出现；不支持 Morph、路径运动或高级入场，不把基础出现描述成这些效果。

先 inspect 获取真实页序与对象名称/ID。检查实际文字和图形对应关系，选择完整的内容对象或分组；组与子对象不能同时选择。

```sh
"$RUNTIME_PYTHON" "$SKILL_DIR/scripts/pptx_motion.py" inspect draft.pptx > work/objects.json
```

动效计划为 JSON，页码按演示顺序从 1 开始。下面名称只是结构示例，制作时必须替换成 inspect 返回的对象名称或 `id:N`：

```json
{
  "transitions": {
    "2": {"effect": "fade", "speed": "med"},
    "3": {"effect": "push", "direction": "l", "speed": "med"}
  },
  "reveals": {
    "3": [["stage-one-label", "stage-one-body"], ["stage-two-group"]]
  }
}
```

同一个内层数组中的对象同时出现，外层数组依次点击。为所有需要转场的页面写入实际计划；不得照抄示例只给第 2、3 页设置。

```sh
"$RUNTIME_PYTHON" "$SKILL_DIR/scripts/pptx_motion.py" apply finalized.pptx --plan work/motion.json --output final-with-motion.pptx > work/motion-report.json
"$RUNTIME_PYTHON" "$SKILL_DIR/scripts/pptx_motion.py" inspect final-with-motion.pptx --require-images --require-transitions --require-reveals > work/final-inspection.json
```

仅按用户实际要求调整检查标志，不能为了让失败检查通过而删掉所需功能。图片检查仅证实图片对象存在，需另外核对 ImageGen 素材来源与实际使用。

工具依据 presentation.xml 关系确定真实页序，兼容绝对与相对关系目标。已有高级兼容性转场分支或已有 timing 的页面不会被盲目覆盖；应改用原生应用编辑或保留已有动效，并核查其符合本次计划。

## 最终文件与验证范围

在会重写 PPTX 的最后一次导出/最终化之后添加效果，再检查最终交付文件。只对未交付的中间稿检查没有意义。工具检查的是包结构、对象引用和步骤数量，不证明 PowerPoint 实际播放体验。

可使用目标应用时在放映模式观察关键转场与点击步骤，确认没有内容永久隐藏、点击次序错乱或节奏不合适。应用不可用时说明“已写入原生效果并检查结构，未实播放映验证”，不得承诺 PowerPoint、WPS 和 Google Slides 完全一致。PNG/PDF 预览不会播放效果。

技术依据：[Microsoft 的动画与转场结构](https://learn.microsoft.com/en-us/office/open-xml/presentation/working-with-animation)。高级效果实现时按官方规范与实际工具能力处理。

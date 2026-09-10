# 课程视频后期工作流

本文记录 2026-07-05 第一课时字幕、去黑边、章节进度条处理后的稳定流程。后续课时优先复用这里的工具链，不要回到低效的临时手工方案。

## 工具优先级

1. 优先使用已安装的 conda-forge FFmpeg：
   `/opt/anaconda3/bin/ffmpeg`
2. 该 FFmpeg 已验证支持 `libass`、`ass`、`subtitles`，适合烧录 ASS/SRT 字幕和章节标签。
3. 当前 conda-forge 构建没有 `drawtext`，中文章节文字使用 `subtitles/libass` 生成临时 ASS 后叠加。
4. 只有在 FFmpeg/libass 不可用时，才使用 `scripts/render_markdown_subtitles.py` 的 Pillow 逐帧渲染兜底方案。
5. 如果电脑空间足够且工具能运行，优先安装和使用更高效、更稳定的工具；安装前说明影响和回滚方法，必要时主动询问用户批准。

## 已安装工具

- conda：`/opt/anaconda3/bin/conda`
- FFmpeg：`/opt/anaconda3/bin/ffmpeg`
- FFprobe：`/opt/anaconda3/bin/ffprobe`
- video-podcast-maker skill：`/Users/yaril/.codex/skills/video-podcast-maker`

验证字幕滤镜：

```bash
/opt/anaconda3/bin/ffmpeg -hide_banner -filters | rg 'draw(text|box)|subtitles|ass'
```

预期至少看到：

```text
ass
drawbox
subtitles
```

## 第一课时最终产物

- 最终推荐视频：`/Users/yaril/个人文档/4 深圳继续教育课程设计/视频/第一课时_去黑边_字幕栏_章节进度条_v1.mp4`
- 上一版叠加字幕视频：`/Users/yaril/个人文档/4 深圳继续教育课程设计/视频/第一课时_去黑边_带字幕_章节进度条_v1.mp4`
- 已带字幕但无章节进度条版本：`/Users/yaril/个人文档/4 深圳继续教育课程设计/视频/第一课时_去黑边_带字幕_v2.mp4`
- 去黑边待加字幕源视频：`/Users/yaril/个人文档/4 深圳继续教育课程设计/视频/第一课时_去黑边_待加字幕_v2.mp4`
- 章节配置：`/Users/yaril/个人文档/4 深圳继续教育课程设计/字幕/第一课时_chapters.json`
- 最终检查帧：`/Users/yaril/个人文档/4 深圳继续教育课程设计/字幕/preview_frames/subtitle_panel_final_2000.png`

中间版本如 `_silent`、普通 `_进度条_v2/v3` 仅用于对比和回滚，不作为最终推荐版本；确认不再需要时可以删除，避免占用空间和混淆版本。

## 独立字幕栏 + 章节进度条（推荐）

当前推荐脚本：

```bash
python3 scripts/add_subtitle_panel_chapter_bar.py INPUT.mp4 SUBTITLES.md CHAPTERS.json OUTPUT.mp4
```

这个脚本会把画布向下扩展，而不是把字幕压到原画面里：

- 上方保留完整视频主体
- 中间新增黑色字幕栏，专门显示字幕
- 下方新增章节进度条
- 音频直接复制，不重新编码

推荐先做 60 秒小样：

```bash
python3 scripts/add_subtitle_panel_chapter_bar.py \
  "视频/第一课时_去黑边_待加字幕_v2.mp4" \
  "字幕/第一课时_字幕审阅稿_v2.md" \
  "字幕/第一课时_chapters.json" \
  "/private/tmp/第一课时_字幕栏样片.mp4" \
  --duration-limit 60 \
  --crf 28 \
  --preset veryfast
```

正式渲染：

```bash
python3 scripts/add_subtitle_panel_chapter_bar.py \
  "视频/第一课时_去黑边_待加字幕_v2.mp4" \
  "字幕/第一课时_字幕审阅稿_v2.md" \
  "字幕/第一课时_chapters.json" \
  "视频/第一课时_去黑边_字幕栏_章节进度条_v1.mp4" \
  --crf 20 \
  --preset medium
```

第一课时当前输出为 `1818x1144`：原视频高度加上约 118 px 字幕栏和 44 px 章节栏。这个高度变化是预期结果，目的是让字幕不遮挡课件和人像区域。

## 章节进度条

仅当输入视频已经带字幕、且确认字幕不会遮挡画面时，才使用这个旧脚本：

脚本：

```bash
python3 scripts/add_chapter_progress_bar.py INPUT.mp4 OUTPUT.mp4 --chapters 字幕/第一课时_chapters.json
```

推荐先做 60 秒小样，确认底部章节栏样式后再跑全片：

```bash
python3 scripts/add_chapter_progress_bar.py \
  "视频/第一课时_去黑边_带字幕_v2.mp4" \
  "/private/tmp/chapter_bar_sample.mp4" \
  --chapters "字幕/第一课时_chapters.json" \
  --duration-limit 60 \
  --crf 28 \
  --preset veryfast
```

正式渲染：

```bash
python3 scripts/add_chapter_progress_bar.py \
  "视频/第一课时_去黑边_带字幕_v2.mp4" \
  "视频/第一课时_去黑边_带字幕_章节进度条_v1.mp4" \
  --chapters "字幕/第一课时_chapters.json" \
  --crf 20 \
  --preset medium
```

脚本会自动读取视频宽高和时长，生成临时 ASS 章节标签，再用 FFmpeg 叠加：

- 底部灰色章节栏
- 黄色章节标题
- 黄色章节分隔线
- 底部蓝色播放进度线

## 章节配置格式

章节配置是 JSON 列表：

```json
[
  { "start": "00:00:00", "label": "引言" },
  { "start": "00:02:28.22", "label": "问题聚焦" }
]
```

要求：

- `start` 支持 `HH:MM:SS.xx`、`MM:SS.xx` 或秒数。
- 第一段必须从 `00:00:00` 开始。
- 最后一段自动延续到视频结尾。
- 标签要短，避免底部栏拥挤。

## 字幕烧录建议

优先使用 ASS/SRT + FFmpeg/libass：

```bash
/opt/anaconda3/bin/ffmpeg \
  -i input.mp4 \
  -vf "subtitles=xxx.ass" \
  -c:v libx264 \
  -crf 20 \
  -preset medium \
  -c:a copy \
  output.mp4
```

如果 ASS 路径包含中文、空格或冒号导致 FFmpeg filter 解析失败，优先把 ASS 临时复制到 `/private/tmp` 的 ASCII 路径，再传给 `subtitles=`。不要为了绕过路径问题退回逐帧渲染。

## 验证清单

每次输出新视频后都要做：

1. 用 `ffprobe` 检查分辨率、时长、音视频流：

   ```bash
   /opt/anaconda3/bin/ffprobe -v error \
     -show_entries format=duration,size \
     -show_entries stream=index,codec_type,codec_name,width,height,duration \
     -of json output.mp4
   ```

2. 抽关键帧检查字幕和章节栏：

   ```bash
   /opt/anaconda3/bin/ffmpeg -y -ss 00:20:00 \
     -i output.mp4 \
     -frames:v 1 \
     -update 1 \
     字幕/preview_frames/check.png
   ```

3. 视觉检查重点：
   - 字幕清晰可读
   - 字幕位于独立字幕栏，不遮挡原视频内容和人像区域
   - 章节栏不盖住字幕主体
   - 进度条没有一开始就铺满
   - 音频时长和视频时长基本一致

## 回滚

本流程不覆盖原视频。需要回滚时直接使用上一阶段产物：

- 原始视频：`视频/第一课时.mov`
- 去黑边待加字幕：`视频/第一课时_去黑边_待加字幕_v2.mp4`
- 已带字幕版本：`视频/第一课时_去黑边_带字幕_v2.mp4`
- 上一版章节进度条版本：`视频/第一课时_去黑边_带字幕_章节进度条_v1.mp4`

建议批量处理后续课时前先提交 git 或创建 branch，避免多个视频中间产物混在一起难以回退。

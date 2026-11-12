"""书稿合规：正文、附录、配套包不写模型名和 DeepSeek Harness（DSH），只说 AI；WorkBuddy 照常写。

先把每个要改的文件备份到本目录 修改前/（保持相对路径），再逐条替换；每条必须恰好出现一次。
参考文献里的论文题名（含 DeepSeek）是引文原文，不改。图片文件名里的 DSH 不是可见文字，不改。
"""
from pathlib import Path
import shutil, re

BOOK = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
J = '/Users/yaril/个人文档/Blender3D/DSH建模测评与教师教程/试做/DSH-01/输出/修订3/'

EDITS = {
    '正文/第01章-从一句话到一张记录页/正文.md': [
        ('WorkBuddy 5.7.7 中进行，模型为 Deepseek-V4.1-Flash，由 AI', 'WorkBuddy 5.7.7 中进行，由 AI'),
    ],
    '正文/第09章-静电的防止与利用/正文.md': [
        ('示范使用 WorkBuddy 5.8.2，模型为 Deepseek-V4.1-Flash。', '示范使用 WorkBuddy 5.8.2。'),
    ],
    '正文/第15章-3D建模和3D打印/正文.md': [
        ('2026 年 10 月，作者改用 DSH（DeepSeek Harness）照着实拍重做了超声波模块',
         '2026 年 10 月，作者改用另一个能调用本机软件的 AI 编程工具，照着实拍重做了超声波模块'),
        ('器件建模用 DSH，标注和色环用 WorkBuddy', '器件建模用这个 AI 编程工具，标注和色环用 WorkBuddy'),
        ('这一步用 DeepSeek Harness（下称 DSH）。它和 WorkBuddy 一样，能读取文件夹里的资料、编写并运行程序；这里由它调用本机的 Blender 生成模型和图片。',
         '这一步用的 AI 编程工具和 WorkBuddy 一样，能读取文件夹里的资料、编写并运行程序；这里由它调用本机的 Blender 生成模型和图片。'),
        ('**准备。** 装好并登录 DSH，装好 Blender。DSH 的设置里，权限选“工作区内修改”，让它只在选定的文件夹里生成和修改文件；初次使用可以关掉“代码工作视图”，先看对话和产物。',
         '**准备。** 装好 Blender，确认所用的 AI 工具能调用它。在 AI 工具的设置里，让它只在选定的文件夹里生成和修改文件；初次使用先看对话和产物。'),
        ('DSH 读到错误，改了程序重新运行', 'AI 读到错误，改了程序重新运行'),
        ('DSH 用了约 16 分钟交出首版', 'AI 用了约 16 分钟交出首版'),
        ('![DSH 交出的首版斜视图', '![AI 交出的首版斜视图'),
        ('可以请 DSH 重新打开保存后的工程', '可以请 AI 重新打开保存后的工程'),
        ('DSH 分别隐藏板边和丝印', 'AI 分别隐藏板边和丝印'),
        ('这次还用同样的任务让 WorkBuddy 独立做了两次，DSH 也另做了一次独立首版，四份首版都有需要人工指出的细节。作者的判断是，器件建模这件事上 DSH 更好用：',
         '这次还用同样的任务让 WorkBuddy 独立做了两次，这个 AI 编程工具也另做了一次独立首版，四份首版都有需要人工指出的细节。作者的判断是，器件建模这件事上这个 AI 编程工具更好用：'),
    ],
    '正文/第15章-3D建模和3D打印/配套/练习材料.md': [
        ('本轮由WorkBuddy 5.7.7、Deepseek-V4.1-Flash实际生成。', '本轮由 WorkBuddy 5.7.7 实际生成。'),
    ],
    '正文/前言-这本书怎么用/正文.md': [
        ('Blender（免费，本书用 5.2.1）和 DeepSeek Harness；', 'Blender（免费，本书用 5.2.1）；'),
    ],
    '正文/附录/附录A-全书提示词.md': [
        ('#### 从实拍建立器件模型（第 1 部分，DeepSeek Harness）', '#### 从实拍建立器件模型（第 1 部分）'),
    ],
    '正文/附录/附录C-WorkBuddy常见问题.md': [
        ('书中操作使用的模型是 Deepseek-V4.1-Flash；器材三维图的标注', '器材三维图的标注'),
        ('第 15 章从实拍建立器件模型这一步用的是 DeepSeek Harness 0.2.1-rc.2（macOS），模型同为 DeepSeek-V4.1-Flash，见该章第三节。',
         '第 15 章从实拍建立器件模型这一步用的是另一个 AI 编程工具，见该章第三节。'),
        ('查看输入区当前选中的模型。本书使用 Deepseek-V4.1-Flash；账号里看到的列表不同时，选一个可用的模型继续，并记下名称。',
         '查看输入区当前选中的模型。账号里看到的列表和书中截图不同时，选一个可用的模型继续，并记下名称。'),
    ],
    '正文/附录/附录D-配套索引.md': [
        ('在 DeepSeek Harness 里作为工作区打开', '在能调用本机 Blender 的 AI 工具里作为工作区打开'),
    ],
    '配套包/配套文件索引.md': [
        ('在 DeepSeek Harness 里作为工作区打开', '在能调用本机 Blender 的 AI 工具里作为工作区打开'),
    ],
    '配套包/配套文件索引.html': [
        ('在 DeepSeek Harness 里作为工作区打开', '在能调用本机 Blender 的 AI 工具里作为工作区打开'),
    ],
    '配套包/第15章/超声波模块-从实拍建模/起步包/开始使用.md': [
        ('本包给已安装并登录DeepSeek Harness、已安装Blender的macOS读者使用。',
         '本包给已安装Blender、并有一个能调用它的AI工具的macOS读者使用。'),
        ('2. 在DSH左侧点击“添加工作区”，选择这份文件夹。\n3. 选择标准模式、工作区内修改权限与要使用的模型。',
         '2. 在AI工具里把这份文件夹设为工作区。\n3. 只允许它在这份文件夹内修改文件。'),
    ],
}


def main():
    for rel, pairs in EDITS.items():
        p = BOOK / rel; s = p.read_text()
        bk = HERE / '修改前' / rel; bk.parent.mkdir(parents=True, exist_ok=True)
        if not bk.exists(): shutil.copy2(p, bk)
        for old, new in pairs:
            assert s.count(old) == 1, (rel, s.count(old), old[:40])
            s = s.replace(old, new)
        p.write_text(s)
    # 核验记录里的本机绝对路径（含 DSH）改为同目录文件名。
    rel = '配套包/第15章/超声波模块-从实拍建模/修订3成品/核验记录.json'
    p = BOOK / rel; bk = HERE / '修改前' / rel; bk.parent.mkdir(parents=True, exist_ok=True)
    if not bk.exists(): shutil.copy2(p, bk)
    s = p.read_text(); assert J in s; p.write_text(s.replace(J, ''))
    # 复查：正文（参考文献除外）与配套包文本里不再出现模型名或 DSH。
    left = []
    for f in list((BOOK / '正文').rglob('*.md')) + [x for x in (BOOK / '配套包').rglob('*') if x.suffix in ('.md', '.txt', '.json', '.html')]:
        if f.name == '参考文献.md': continue
        t = f.read_text(errors='ignore')
        t = re.sub(r'data:[^"\')\s]+', '', t)  # 嵌入图片的 base64 不算
        t = re.sub(r'\]\([^)]*\)|src="[^"]*"', '', t)  # 文件路径不算可见文字
        if re.search(r'(?i)deepseek|(?<![A-Za-z])DSH(?![A-Za-z])', t): left.append(str(f.relative_to(BOOK)))
    print('仍含模型名或 DSH 的文件：', left or '无')


if __name__ == '__main__':
    main()

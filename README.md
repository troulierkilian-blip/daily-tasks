# 每日任务 · Windows 离线待办清单

简体中文 · [English](README.en.md)

昨天没写完的周报，今天可以接着写。打开昨天的清单，点「复制到今天」，标题、备注和优先级都会带过来。昨天那条仍保留当时的进度，今天完成的工作记在今天。

**[下载 Windows x64 免安装版](https://github.com/troulierkilian-blip/daily-tasks/releases/latest/download/DailyTasks-Windows-x64.exe)** · [发布说明与 SHA-256 校验值](https://github.com/troulierkilian-blip/daily-tasks/releases/latest)

适用于 Windows 10 / 11 x64。双击 EXE 即可使用，无需联网、注册或安装 Python。

![今天的任务清单：从昨天复制的「整理周报」排在高优先级，状态为待开始](docs/today.png)

## 把昨天的任务接到今天

1. **记一条任务。** 点「新增任务」（`Ctrl+N`），填写标题、日期、优先级和备注。开始处理时，把状态从「待开始」改为「进行中」。
2. **隔天继续。** 在左侧日历点昨天，在未完成任务右边点 **「… → 复制到今天」**。点「今天」就能看到一条新的待开始任务；做完后点左侧圆圈即可标为已完成。
3. **回看两天的进度。** 进入「历史记录」，搜索标题或备注。下图中，昨天的「整理周报」是进行中，今天的副本已完成。点 **「导出 CSV」**，就能在 Excel 中打开这两条筛选结果。

![在历史记录中搜索「整理周报」，可见两个日期各自的状态与完成时间](docs/history.png)

## 统计与备份

「完成统计」可以查看当天、近七天和本月的完成率。任务自动保存在本机，通常位于 `%LOCALAPPDATA%\DailyTasks\tasks.db`。换电脑时，在「数据与备份」导出完整数据库，再在新电脑恢复。筛选、快捷键和恢复步骤见[使用说明](使用说明.md)。

## 从源码运行

在安装了 64 位 Python 3.10 的 Windows 电脑上，进入项目目录并运行以下 PowerShell 命令。

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe main.py
```

运行 `powershell -ExecutionPolicy Bypass -File .\重新打包.ps1` 可执行测试并生成 `dist\每日任务.exe`。第三方组件的许可文本见 [licenses](licenses/)。

## 支持项目

如果「每日任务」帮到了你，欢迎通过支付宝或微信扫码打赏。感谢你的支持！

| 支付宝 | 微信 |
| :---: | :---: |
| <img src="assets/sponsors/alipay.jpg" alt="支付宝收款码" width="220"> | <img src="assets/sponsors/wechat.jpg" alt="微信收款码" width="220"> |

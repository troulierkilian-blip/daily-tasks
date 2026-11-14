# 每日任务

每日任务是一款中文 Windows 桌面软件。你可以按日期安排任务，在「待开始」「进行中」「已完成」之间切换，并查看每天的完成情况。记录自动保存在本机，可离线使用。

**[下载 Windows 64 位免安装版](https://github.com/troulierkilian-blip/daily-tasks/releases/download/v1.0.0/DailyTasks-Windows-x64.exe)** · [查看 v1.0.0 发布说明与文件校验值](https://github.com/troulierkilian-blip/daily-tasks/releases/tag/v1.0.0)

在 Windows 10 或 11 的 64 位电脑上双击下载的 exe，点击「新增任务」即可开始使用。

## 日常使用

- 在日历中选择日期，为任务设置优先级、填写备注并更新状态。
- 从某一天的任务菜单选择「复制到今天」，可以继续处理过去未完成的工作，同时保留当时的记录。
- 按关键词、日期范围和状态查找历史任务，将当前筛选结果导出为 Excel 可打开的 CSV。
- 查看当天、近七天和本月的完成率，通过「数据与备份」备份记录或迁移到另一台电脑。

更多操作见[使用说明](使用说明.md)。

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

$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
Set-Location -LiteralPath $taskRoot
$taskPython = Join-Path $taskRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $taskPython)) {
    python -m venv (Join-Path $taskRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw '创建 Python 虚拟环境失败。' }
}
& $taskPython -m pip install -r (Join-Path $taskRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw '安装依赖失败。' }
& $taskPython -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw '功能测试失败，已停止打包。' }
& $taskPython (Join-Path $taskRoot 'build.py')
if ($LASTEXITCODE -ne 0) { throw 'exe 打包失败。' }
Write-Host '打包完成：dist\每日任务.exe'

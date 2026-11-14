"""Verify the standalone executable with no source, Python or Qt on PATH."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[1]
executable = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'dist' / '每日任务.exe'
folder = ROOT / 'artifacts' / 'exe-verification'
standalone = folder / 'standalone'
standalone.mkdir(parents=True, exist_ok=True)
copied = standalone / '每日任务.exe'
shutil.copy2(executable, copied)
assert sorted(path.name for path in standalone.iterdir()) == ['每日任务.exe']
data = folder / ('data-' + str(time.time_ns()))
environment = os.environ.copy()
environment['PATH'] = os.path.join(environment.get('SystemRoot', 'C:\\Windows'), 'System32')
environment['QT_QPA_PLATFORM'] = 'windows'
for name in ('PYTHONPATH', 'PYTHONHOME', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH'):
    environment.pop(name, None)
results = []
for phase, scale in [('write', '1'), ('read', '1.25')]:
    environment['QT_SCALE_FACTOR'] = scale
    report = folder / (phase + '.json')
    screenshot = folder / (phase + '.png')
    start = time.perf_counter()
    command = [str(copied), '--data-dir', str(data), '--smoke-test', phase,
               '--smoke-report', str(report), '--screenshot', str(screenshot)]
    process = subprocess.run(command, cwd=standalone, env=environment, timeout=90,
                             creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True)
    duration = round(time.perf_counter() - start, 2)
    if process.returncode != 0:
        raise RuntimeError(f'{phase} exe failed: {process.returncode}; '
                           f'{process.stdout.decode(errors="replace")} '
                           f'{process.stderr.decode(errors="replace")}')
    result = json.loads(report.read_text(encoding='utf-8'))
    assert result['ok'] and result['frozen'], result
    assert screenshot.is_file()
    results.append({**result, 'seconds': duration, 'scale': scale})
assert results[0]['task_id'] == results[1]['task_id'], '重开后任务不一致'
image = pefile.PE(str(executable), fast_load=True)
machine, subsystem = image.FILE_HEADER.Machine, image.OPTIONAL_HEADER.Subsystem
image.close()
assert machine == 0x8664, '不是 Windows 64 位文件'
assert subsystem == 2, '不是无控制台的桌面程序'
summary = {'ok': True, 'executable': str(executable), 'bytes': executable.stat().st_size,
           'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
           'architecture': 'AMD64', 'subsystem': 'Windows GUI',
           'standalone_directory_files': ['每日任务.exe'], 'runs': results}
(folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))

"""Reproducible Windows one-file build; run using the project virtual environment."""

import os
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path


def prepare_assets(root):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
    from dailytasks.gui import app_icon
    assets = root / 'assets'
    assets.mkdir(exist_ok=True)
    png, icon_file = assets / 'icon.png', assets / 'icon.ico'
    if not app_icon().pixmap(256, 256).save(str(png), 'PNG'):
        raise RuntimeError('图标生成失败。')
    image = png.read_bytes()
    icon_file.write_bytes(struct.pack('<HHH', 0, 1, 1) +
        struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(image), 22) + image)
    arrow = QPixmap(20, 20)
    arrow.fill(Qt.GlobalColor.transparent)
    painter = QPainter(arrow)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#8590a4'), 2.2, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.drawLine(QPointF(4, 7), QPointF(10, 13))
    painter.drawLine(QPointF(10, 13), QPointF(16, 7))
    painter.end()
    if not arrow.save(str(assets / 'chevron-down.png'), 'PNG'):
        raise RuntimeError('下拉框图标生成失败。')
    return icon_file


def main():
    root = Path(__file__).resolve().parent
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise SystemExit('请使用 Windows 64 位 Python 进行打包。')
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6 import __file__ as qt_file
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    icon_file = prepare_assets(root)
    del app
    licenses = root / 'licenses'
    licenses.mkdir(exist_ok=True)
    package = Path(qt_file).parent
    for location in (package / 'Qt' / 'licenses', package / 'licenses'):
        if location.is_dir():
            for source in location.rglob('*'):
                if source.is_file():
                    relative = source.relative_to(location)
                    destination = licenses / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
    # Include the wheel's own license notices, including commercial-option notices.
    for info in package.parent.glob('*.dist-info'):
        if info.name.lower().startswith(('pyside6', 'shiboken6', 'pyinstaller')):
            notice_dir = info / 'licenses'
            if notice_dir.is_dir():
                shutil.copytree(notice_dir, licenses / info.name, dirs_exist_ok=True)
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if python_license.exists():
        shutil.copy2(python_license, licenses / 'Python-LICENSE.txt')
    (licenses / '第三方说明.txt').write_text(
        '本软件使用 Python、SQLite、PySide6/Qt 和 PyInstaller。\n'
        'PySide6/Qt：LGPLv3 / GPL / 商业许可。此项目使用 LGPLv3 发行组件。\n'
        'Qt 库保持动态链接，源码及构建脚本随软件提供，可自行更换库后重新构建。\n'
        'PySide6 源码：https://code.qt.io/pyside/pyside-setup.git\n'
        'Qt 源码：https://code.qt.io/qt/\n'
        'Python：https://www.python.org/psf/license/\n'
        'SQLite：https://sqlite.org/copyright.html\n'
        'PyInstaller：https://pyinstaller.org/en/stable/license.html\n', encoding='utf-8')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
               '--windowed', '--noupx', '--name', '每日任务', '--icon', str(icon_file),
               '--distpath', str(root / 'dist'), '--workpath', str(root / 'build' / 'pyinstaller'),
               '--specpath', str(root / 'build'), '--add-data', str(licenses) + ';licenses',
               '--add-data', str(root / 'assets') + ';assets',
               '--exclude-module', 'tkinter', '--exclude-module', 'numpy',
               '--exclude-module', 'matplotlib', '--exclude-module', 'PySide6.QtQml',
               '--exclude-module', 'PySide6.QtQuick', str(root / 'main.py')]
    # A workstation may have unrelated ICU libraries on PATH (for example Poppler).
    # Qt on Windows imports the OS ICU ABI; bundling another ICU breaks QtCore.
    # Restrict dependency discovery to this Python/Qt and Windows system folders.
    environment = os.environ.copy()
    windows = Path(os.environ.get('SystemRoot', 'C:/Windows'))
    environment['PATH'] = os.pathsep.join([str(package), str(package.parent / 'shiboken6'),
        sys.base_prefix, str(windows / 'System32'), str(windows)])
    subprocess.run(command, cwd=root, env=environment, check=True)
    for filename in ('使用说明.md',):
        shutil.copy2(root / filename, root / 'dist' / filename)
    shutil.copytree(licenses, root / 'dist' / '第三方许可', dirs_exist_ok=True)
    source_paths = [root / name for name in ('main.py', 'build.py', 'requirements.txt',
        'requirements-lock.txt', '重新打包.ps1', '使用说明.md', '.gitignore')]
    for folder in ('dailytasks', 'tests', 'tools', 'assets', 'licenses'):
        source_paths.extend(path for path in (root / folder).rglob('*')
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc')
    with zipfile.ZipFile(root / 'dist' / '每日任务-源码.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in source_paths:
            archive.write(path, path.relative_to(root).as_posix())
    executable = root / 'dist' / '每日任务.exe'
    print(f'已生成：{executable}\n大小：{executable.stat().st_size / 1024 / 1024:.1f} MB')


if __name__ == '__main__':
    main()

"""在本机已有字体下串行导出 PDF；不会操作 WPS 中的其他文档。"""
from pathlib import Path
import os, subprocess

HERE = Path(__file__).resolve().parent
converter = Path('/Users/yaril/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice')
env = dict(os.environ, TMPDIR='/private/tmp', OMP_NUM_THREADS='1',
           FONTCONFIG_FILE=str(HERE/'本机字体配置.xml'),
           XDG_CACHE_HOME='/private/tmp/book-font-cache-20261015')
subprocess.run([str(converter),
                '-env:UserInstallation=file:///private/tmp/book-pdf-20261015-font-profile',
                '--headless', '--convert-to', 'pdf', '--outdir', str(HERE),
                str(HERE/'全书排版稿.docx')], env=env, check=True, timeout=180)
print(HERE/'全书排版稿.pdf')

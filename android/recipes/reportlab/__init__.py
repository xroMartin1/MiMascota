"""Modern ReportLab is pure Python; avoid the legacy Mercurial/C-extension recipe."""
from pythonforandroid.recipe import PythonRecipe


class ReportLabRecipe(PythonRecipe):
    version = '4.4.10'
    url = 'https://files.pythonhosted.org/packages/48/57/28bfbf0a775b618b6e4d854ef8dd3f5c8988e5d614d8898703502a35f61c/reportlab-4.4.10.tar.gz'
    # PyPI source SHA256: 5cbbb34ac3546039d0086deb2938cdec06b12da3cdb836e813258eb33cd28487
    depends = ['python3', 'pillow']
    site_packages_name = 'reportlab'
    call_hostpython_via_targetpython = False
    setup_extra_args = ['--no-deps']


recipe = ReportLabRecipe()

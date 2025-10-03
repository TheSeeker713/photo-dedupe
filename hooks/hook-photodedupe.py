# PyInstaller hook for Qt resources and photo-dedupe modules

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect Qt platform plugins and resources
datas = collect_data_files('PySide6')

# Collect all submodules for our application
hiddenimports = []
hiddenimports += collect_submodules('src')
hiddenimports += collect_submodules('src.app')
hiddenimports += collect_submodules('src.gui')
hiddenimports += collect_submodules('src.ui')
hiddenimports += collect_submodules('src.core')
hiddenimports += collect_submodules('src.ops')

# Ensure Qt plugins are included
hiddenimports += [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtOpenGL',
]
# PyInstaller: onedir-Bundle (Qt/PySide6-sicherer als onefile)
# Aufruf aus Repo-Root: pyinstaller packaging/pyinstaller/openstair.spec

from pathlib import Path

try:
    from PyInstaller.utils.hooks import collect_all
except ImportError:
    collect_all = None  # type: ignore[misc,assignment]

# Repo-Root: packaging/pyinstaller -> ..
_repo = Path(__file__).resolve().parents[2]

_datas: list = [
    (str(_repo / "data"), "data"),
    (str(_repo / "app"), "app"),
]

_bin: list = []
_hid: list = [
    "export",
    "export.dxf",
    "ui",
    "core",
    "config",
    "dxf_export",
    "dxf_settings",
    "ui.dxf_settings_dialog",
    "ui.stair_preview",
    "calculations",
    "norms",
    "enums",
    "profile_library",
    "report_export",
]

if collect_all is not None:
    try:
        d_extra, b_extra, hi_extra = collect_all("PySide6")
        _datas += d_extra
        _bin += b_extra
        _hid += list(hi_extra)
    except Exception:  # noqa: BLE001
        pass

a = Analysis(
    [str(_repo / "main.py")],
    pathex=[str(_repo)],
    binaries=_bin,
    datas=_datas,
    hiddenimports=_hid,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

_icon = _repo / "app" / "openstair-icon.png"
_ico = str(_icon) if _icon.is_file() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="openstair",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_ico,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="openstair",
)

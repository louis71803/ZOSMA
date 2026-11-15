# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller Specification for Z.O.S.M.A. Native Desktop HUD (`packaging/zosma.spec`).

Produces `dist/ZOSMA_HUD/ZOSMA.exe` (`--onedir` layout) with:
1. Full offline Streamlit + st.components.v2 + PyWebView (Edge WebView2) runtime inside `_internal/`.
2. Live, editable `app.py`, `core/`, `modules/`, `ui/`, `data/`, and `.streamlit/` placed directly in
   `dist/ZOSMA_HUD/` root so:
   - `Path(__file__).resolve()` inside all 5 domain modules resolves `data/<module_id>/` identically
     to local development without modifying a single line of teammate code.
   - `data/runtime_session.json` and `data/crew_records/*.json` remain writable next to `ZOSMA.exe`.
   - Teammates (Roles 2-6) can drop updated `modules/*.py` or `data/<module_id>/*.csv` directly into
     the packaged folder (or re-run `packaging/build_exe.bat`) without touching virtual environments.
"""

from pathlib import Path
import shutil
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

SPEC_DIR = Path(SPECPATH).resolve()
PROJECT_ROOT = SPEC_DIR.parent

datas = []
binaries = []
hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.web.bootstrap",
    "streamlit.web.server.server",
    "streamlit.web.server.starlette",
    "streamlit.runtime",
    "streamlit.runtime.scriptrunner",
    "streamlit.components.v1",
    "streamlit.components.v2",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "starlette",
    "webview",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
    "clr",
    "clr_loader",
    "pythonnet",
    "PIL",
    "PIL.Image",
    "pandas",
    "numpy",
    "scipy",
    "scipy.stats",
    "scipy.signal",
    "scipy.integrate",
    "scipy.interpolate",
    "plotly",
    "plotly.graph_objects",
    "plotly.subplots",
    "matplotlib",
    "matplotlib.pyplot",
    "pydantic",
    "yaml",
]

for pkg in ("streamlit", "webview", "plotly", "altair", "pydeck", "pydantic", "PIL", "pythonnet", "clr_loader"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

for pkg in ("streamlit", "webview", "uvicorn", "starlette", "pydantic", "scipy"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

for pkg in ("pythonnet", "clr_loader", "webview"):
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

for meta_pkg in (
    "streamlit",
    "pywebview",
    "plotly",
    "altair",
    "pandas",
    "numpy",
    "scipy",
    "matplotlib",
    "pydantic",
    "pyyaml",
    "pillow",
    "uvicorn",
    "starlette",
):
    try:
        datas += copy_metadata(meta_pkg)
    except Exception:
        pass

# Exclude workspace packages from frozen PYZ archive so Python loads live files from dist/ZOSMA_HUD/
# and also exclude unrelated heavy AI/cloud packages installed in the Conda environment.
excludes = [
    "core",
    "modules",
    "ui",
    "litellm",
    "litellm_enterprise",
    "litellm_proxy_extras",
    "openai",
    "vertexai",
    "vertex_ray",
    "google.cloud",
    "boto3",
    "botocore",
    "azure",
    "huggingface_hub",
    "tokenizers",
    "tiktoken",
    "polars",
    "_polars_runtime_32",
    "psycopg",
    "psycopg_binary",
    "redis",
    "rq",
    "grpc",
    "fastapi",
    "PyInstaller",
]

a = Analysis(
    [str(SPEC_DIR / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ZOSMA",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(SPEC_DIR / "zosma_app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="ZOSMA_HUD",
)


def _sync_project_tree_into_dist() -> None:
    """Copy live `app.py`, `core/`, `modules/`, `ui/`, `.streamlit/`, and clean `data/` into `dist/ZOSMA_HUD/`."""
    dist_dir = Path(DISTPATH).resolve() / "ZOSMA_HUD"
    if not dist_dir.exists():
        return

    # 1. Copy top-level app.py and requirements.txt
    for fname in ("app.py", "requirements.txt"):
        src_file = PROJECT_ROOT / fname
        if src_file.exists():
            shutil.copy2(src_file, dist_dir / fname)

    # 2. Copy live source trees (`core/`, `modules/`, `ui/`, `.streamlit/`)
    ignore_patterns = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store", "Thumbs.db")
    for folder_name in ("core", "modules", "ui", ".streamlit"):
        src_folder = PROJECT_ROOT / folder_name
        dst_folder = dist_dir / folder_name
        if src_folder.exists():
            if dst_folder.exists():
                shutil.rmtree(dst_folder)
            shutil.copytree(src_folder, dst_folder, ignore=ignore_patterns)

    # 3. Copy `data/` subdirectories while excluding local developer session state
    src_data = PROJECT_ROOT / "data"
    dst_data = dist_dir / "data"
    dst_data.mkdir(parents=True, exist_ok=True)
    if src_data.exists():
        for item in src_data.iterdir():
            if item.name in {"runtime_session.json", "crew_records", "__pycache__"}:
                continue
            target = dst_data / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target, ignore=ignore_patterns)
            elif item.is_file():
                shutil.copy2(item, target)
    (dst_data / "crew_records").mkdir(parents=True, exist_ok=True)


_sync_project_tree_into_dist()

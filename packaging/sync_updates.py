"""Quick Update Synchronizer for Packaged `dist/ZOSMA_HUD/` (`packaging/sync_updates.py`).

When teammates (Roles 2-6) update `modules/*.py` or drop new CSV/JSON files into `data/`,
you do NOT need to wait for a full PyInstaller rebuild — run:
    python packaging/sync_updates.py
to instantly sync `app.py`, `core/`, `modules/`, `ui/`, `.streamlit/`, and `data/`
into `dist/ZOSMA_HUD/`.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys


def sync_into_dist() -> int:
    project_root = Path(__file__).resolve().parent.parent
    dist_dir = project_root / "dist" / "ZOSMA_HUD"
    if not dist_dir.exists():
        print(f"[ERROR] {dist_dir} does not exist yet. Run `packaging\\build_exe.bat` first.")
        return 1

    for fname in ("app.py", "requirements.txt"):
        src_file = project_root / fname
        if src_file.exists():
            shutil.copy2(src_file, dist_dir / fname)

    ignore_patterns = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store", "Thumbs.db")
    for folder_name in ("core", "modules", "ui", ".streamlit"):
        src_folder = project_root / folder_name
        dst_folder = dist_dir / folder_name
        if src_folder.exists():
            if dst_folder.exists():
                shutil.rmtree(dst_folder)
            shutil.copytree(src_folder, dst_folder, ignore=ignore_patterns)

    src_data = project_root / "data"
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

    print(f"[OK] Synced latest app.py, core/, modules/, ui/, and data/ -> {dist_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(sync_into_dist())

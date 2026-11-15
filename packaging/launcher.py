"""Z.O.S.M.A. Native Desktop Application Launcher (`packaging/launcher.py`).

Starts the local offline Streamlit server in a daemon thread (without triggering
`signal.signal` ValueError in non-main threads) and opens a native `pywebview`
(Edge WebView2) desktop window on the main thread. When the window closes, the
process exits cleanly.
"""

from __future__ import annotations

import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser


def resolve_app_root() -> Path:
    """Resolve the writable application root containing `app.py`, `core/`, `modules/`, `ui/`, and `data/`."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "app.py").exists():
            return exe_dir
        meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
        if (meipass / "app.py").exists():
            return meipass
        return exe_dir
    return Path(__file__).resolve().parent.parent


def find_free_port(preferred: int = 8501) -> int:
    """Find an available localhost TCP port."""
    for port in (preferred, 8502, 8503, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return int(s.getsockname()[1])
            except OSError:
                continue
    return preferred


def wait_for_server(url: str, timeout_s: float = 35.0) -> bool:
    """Poll the Streamlit health endpoint until it responds."""
    health_url = f"{url.rstrip('/')}/_stcore/health"
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False


def _start_streamlit_in_background(app_script: Path, port: int) -> None:
    """Run Streamlit's Starlette/Uvicorn server inside a background thread."""
    from streamlit import config as st_config
    from streamlit.web import bootstrap

    # Prevent signal.signal() from raising ValueError inside a non-main thread
    bootstrap._set_up_signal_handler = lambda server: None  # type: ignore[assignment]

    flag_options = {
        "server_port": port,
        "server_address": "127.0.0.1",
        "server_headless": True,
        "browser_gatherUsageStats": False,
        "global_developmentMode": False,
        "client_toolbarMode": "minimal",
    }
    st_config.set_option("global.developmentMode", False)
    st_config.set_option("server.port", port)
    st_config.set_option("server.address", "127.0.0.1")
    st_config.set_option("server.headless", True)
    st_config.set_option("browser.gatherUsageStats", False)
    st_config.set_option("client.toolbarMode", "minimal")

    bootstrap.run(
        str(app_script),
        False,
        [],
        flag_options,
    )


def _open_fallback_app_window(url: str) -> None:
    """Fallback if Edge WebView2 runtime is unavailable on a target machine."""
    edge_candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    ]
    for edge in edge_candidates:
        if edge.exists():
            subprocess.Popen([str(edge), f"--app={url}", "--start-maximized"])
            return
    webbrowser.open(url)


def main() -> None:
    app_root = resolve_app_root()
    os.chdir(app_root)
    if str(app_root) not in sys.path:
        sys.path.insert(0, str(app_root))

    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    app_script = app_root / "app.py"
    port = find_free_port(8501)
    url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(
        target=_start_streamlit_in_background,
        args=(app_script, port),
        daemon=True,
        name="zosma-streamlit-server",
    )
    server_thread.start()

    # Support automated smoke-test mode (--smoke-test) so CI/build scripts can verify startup
    if "--smoke-test" in sys.argv:
        ok = wait_for_server(url, timeout_s=35.0)
        print(f"SMOKE_TEST_SERVER_READY={ok} URL={url}", flush=True)
        sys.exit(0 if ok else 1)

    wait_for_server(url, timeout_s=35.0)

    try:
        import webview

        webview.create_window(
            title="Z.O.S.M.A. — Deep-Space Astronaut Health Monitoring System",
            url=url,
            width=1540,
            height=940,
            min_size=(1180, 740),
            background_color="#04070f",
            text_select=True,
        )
        webview.start()
    except Exception:
        _open_fallback_app_window(url)
        try:
            while server_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            pass

    os._exit(0)


if __name__ == "__main__":
    main()

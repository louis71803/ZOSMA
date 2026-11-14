"""Clean Assembler Entrypoint for Z.O.S.M.A. SpaceX HUD (`ui/hud_assets.py`).

Role 1's frontend is cleanly split across modular files:
- `ui/styles.py`         : Glassmorphism CSS, animations, and responsive grid
- `ui/i18n.py`           : Bilingual EN / 繁體中文 UI & domain corpus dictionaries
- `ui/anatomy_svgs.py`   : 5-subsystem interactive holographic vector anatomy & habitat SVGs
- `ui/hud_controller.py` : Client-side state controller, trend chart, and drawer events

`app.py` imports `HUD_HTML`, `HUD_CSS`, and `HUD_JS` directly from here with zero breaking changes.
"""

from __future__ import annotations

from ui.hud_controller import build_hud_js
from ui.styles import HUD_CSS, HUD_HTML

HUD_JS: str = build_hud_js()

__all__ = ["HUD_HTML", "HUD_CSS", "HUD_JS"]

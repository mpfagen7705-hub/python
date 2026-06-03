"""Force pygame into headless mode so rendering code can be smoke-tested in CI.

Must run before pygame is imported anywhere, so it lives in conftest at import
time rather than inside a fixture.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

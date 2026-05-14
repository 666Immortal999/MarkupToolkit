import os

# Reduce noisy Qt platform warnings on some Windows display driver setups.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.screen=false;qt.qpa.window=false")

from core.app import run


if __name__ == "__main__":
    run()

"""py2app setup for Grasp.app.

Usage:
    pip install -r requirements.txt py2app
    python setup.py py2app
"""

from setuptools import setup

APP = ["grasp_main.py"]
DATA_FILES = []

PLIST = {
    "CFBundleName": "Grasp",
    "CFBundleDisplayName": "Grasp",
    "CFBundleIdentifier": "com.grasp.app",
    "CFBundleVersion": "1.0.0",
    "CFBundleShortVersionString": "1.0.0",
    "CFBundleExecutable": "Grasp",
    # Menubar-only — no Dock icon, no main menu.
    "LSUIElement": True,
    "NSHighResolutionCapable": True,
    "NSSupportsAutomaticGraphicsSwitching": True,
    "LSMinimumSystemVersion": "11.0",
    # Usage strings — required so macOS knows what to show in permission prompts.
    "NSAppleEventsUsageDescription": (
        "Grasp synthesizes a copy keystroke to read your selected text."
    ),
    "NSAccessibilityUsageDescription": (
        "Grasp needs Accessibility access to listen for the ⌘⇧Space hotkey "
        "and to read the text you have highlighted."
    ),
}

OPTIONS = {
    "argv_emulation": False,
    "plist": PLIST,
    "packages": ["grasp", "rumps", "anthropic"],
    "includes": ["pyperclip", "objc"],
    "excludes": ["tkinter"],
    "strip": True,
}

setup(
    app=APP,
    name="Grasp",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

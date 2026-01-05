#!/usr/bin/env python3
"""
3D All Stars Linux Edition - Simple Installer
Author: retired64
License: MIT
"""

import os
import sys
import subprocess
import shutil
import urllib.request
from pathlib import Path

# ============================================================================
# CONFIG
# ============================================================================

REPO_URL = "https://github.com/retired64/3D-All-Stars-Linux-EDITION.git"
REPO_NAME = "3D-All-Stars-Linux-EDITION"
ICON_URL = "https://raw.githubusercontent.com/retired64/3D-All-Stars-Linux-EDITION/main/src/img/icon.png"

HOME = Path.home()
INSTALL_DIR = HOME / REPO_NAME
LOCAL_SHARE = HOME / ".local" / "share"
ICONS_DIR = LOCAL_SHARE / "icons"
APPS_DIR = LOCAL_SHARE / "applications"
LAUNCHER = INSTALL_DIR / "launcher.sh"
DESKTOP = APPS_DIR / "3d-all-stars.desktop"
ICON = ICONS_DIR / "3d-all-stars.png"

# ============================================================================
# UTILS
# ============================================================================

def run(cmd, check=True):
    """Run command"""
    try:
        subprocess.run(cmd, check=check, shell=isinstance(cmd, str))
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if check:
            sys.exit(1)

def log(msg, level="info"):
    """Simple logger"""
    icon = {"info": "🔵", "warn": "⚠️", "ok": "✅", "error": "❌"}
    print(f"{icon.get(level, '•')} {msg}")

def check_tool(cmd):
    """Check if command exists"""
    if not shutil.which(cmd):
        log(f"Missing: {cmd}", "error")
        log(f"Install: sudo apt install {cmd}", "warn")
        sys.exit(1)

# ============================================================================
# INSTALLER
# ============================================================================

class Installer:
    def __init__(self):
        self.print_header()
        self.check_deps()
    
    def print_header(self):
        print("\n" + "=" * 60)
        print("  3D ALL STARS LINUX EDITION - INSTALLER")
        print("=" * 60 + "\n")
    
    def check_deps(self):
        """Check system dependencies"""
        log("Checking dependencies")
        for tool in ['git', 'python3']:
            check_tool(tool)
    
    def clone_repo(self):
        """Clone repository"""
        log("Cloning repository")
        
        if INSTALL_DIR.exists():
            log(f"Directory exists: {INSTALL_DIR}", "warn")
        else:
            run(["git", "clone", "--depth=1", REPO_URL, str(INSTALL_DIR)])
        
        os.chdir(INSTALL_DIR)
        run(["git", "lfs", "install"], check=False)
        run(["git", "lfs", "pull"], check=False)
    
    def setup_python(self):
        """Setup Python environment"""
        log("Setting up Python environment")
        
        venv = INSTALL_DIR / ".venv"
        if not venv.exists():
            run([sys.executable, "-m", "venv", str(venv)])
        
        pip = venv / "bin" / "pip"
        reqs = INSTALL_DIR / "requirements.txt"
        
        if reqs.exists():
            run([str(pip), "install", "-q", "--upgrade", "pip"])
            run([str(pip), "install", "-q", "-r", str(reqs)])
    
    def setup_icon(self):
        """Download icon"""
        log("Setting up icon")
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            urllib.request.urlretrieve(ICON_URL, ICON)
        except Exception as e:
            log(f"Icon download failed: {e}", "warn")
    
    def create_launcher(self):
        """Create launcher script"""
        log("Creating launcher")
        
        script = f"""#!/bin/bash
cd "{INSTALL_DIR}"
source .venv/bin/activate
python3 main.py "$@"
"""
        LAUNCHER.write_text(script)
        LAUNCHER.chmod(0o755)
    
    def create_desktop(self):
        """Create desktop entry"""
        log("Creating desktop entry")
        APPS_DIR.mkdir(parents=True, exist_ok=True)
        
        entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Super Mario 3D All Stars
Comment=3D All Stars Linux Edition
Icon={ICON}
Exec={LAUNCHER}
Path={INSTALL_DIR}
Terminal=false
Categories=Game;Emulator;
"""
        DESKTOP.write_text(entry)
        DESKTOP.chmod(0o644)
    
    def set_permissions(self):
        """Set executable permissions"""
        log("Setting permissions")
        
        executables = [
            "dolphin-emulator/dolphin-emu",
            "3ds/azahar.AppImage",
            "nds/melonDS",
            "main.py"
        ]
        
        for exe in executables:
            path = INSTALL_DIR / exe
            if path.exists():
                path.chmod(path.stat().st_mode | 0o111)
        
        # Game scripts
        games = INSTALL_DIR / "games"
        if games.exists():
            for script in games.glob("*/run"):
                script.chmod(script.stat().st_mode | 0o111)
    
    def refresh_desktop(self):
        """Refresh desktop database"""
        log("Refreshing desktop")
        run(f"update-desktop-database {APPS_DIR}", check=False)
        run(f"gtk-update-icon-cache {ICONS_DIR}", check=False)
    
    def run(self):
        """Run installation"""
        try:
            self.clone_repo()
            self.setup_python()
            self.setup_icon()
            self.create_launcher()
            self.create_desktop()
            self.set_permissions()
            self.refresh_desktop()
            self.print_success()
        
        except KeyboardInterrupt:
            log("\nCancelled by user", "warn")
            sys.exit(130)
        except Exception as e:
            log(f"Installation failed: {e}", "error")
            sys.exit(1)
    
    def print_success(self):
        """Print success message"""
        print("\n" + "=" * 60)
        print("  ✅ INSTALLATION COMPLETE!")
        print("=" * 60)
        print(f"\nInstalled: {INSTALL_DIR}")
        print("\n🎮 Launch:")
        print(f"  • Applications Menu → Super Mario 3D All Stars")
        print(f"  • Or run: {LAUNCHER}")
        print("\n💡 If icon doesn't appear:")
        print("  • Log out and back in")
        print(f"  • Or: update-desktop-database {APPS_DIR}")
        print("\n" + "=" * 60 + "\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    installer = Installer()
    installer.run()

if __name__ == "__main__":
    main()

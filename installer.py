#!/usr/bin/env python3
"""
3D All Stars Linux Edition - Universal Multi-Distro Installer
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
# DISTRO DETECTION & PACKAGE MANAGEMENT
# ============================================================================

class DistroManager:
    """Detects Linux distro and provides package management commands"""
    
    def __init__(self):
        self.distro = self.detect_distro()
        self.pkg_manager = self.get_package_manager()
    
    def detect_distro(self):
        """Detect Linux distribution"""
        if Path("/etc/os-release").exists():
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content or "debian" in content or "mint" in content:
                    return "debian"
                elif "fedora" in content or "rhel" in content or "centos" in content:
                    return "fedora"
                elif "arch" in content or "manjaro" in content:
                    return "arch"
                elif "opensuse" in content or "suse" in content:
                    return "suse"
                elif "gentoo" in content:
                    return "gentoo"
                elif "alpine" in content:
                    return "alpine"
                elif "void" in content:
                    return "void"
        return "unknown"
    
    def get_package_manager(self):
        """Get package manager for distro"""
        managers = {
            "debian": ("apt", "apt-get"),
            "fedora": ("dnf", "yum"),
            "arch": ("pacman",),
            "suse": ("zypper",),
            "gentoo": ("emerge",),
            "alpine": ("apk",),
            "void": ("xbps-install",)
        }
        
        if self.distro in managers:
            for mgr in managers[self.distro]:
                if shutil.which(mgr):
                    return mgr
        
        # Fallback: check common package managers
        for mgr in ["apt", "dnf", "pacman", "zypper", "emerge", "apk", "xbps-install"]:
            if shutil.which(mgr):
                return mgr
        
        return None
    
    def get_install_command(self, packages):
        """Get install command for package manager"""
        if not self.pkg_manager:
            return None
        
        commands = {
            "apt": ["sudo", "apt", "install", "-y"] + packages,
            "apt-get": ["sudo", "apt-get", "install", "-y"] + packages,
            "dnf": ["sudo", "dnf", "install", "-y"] + packages,
            "yum": ["sudo", "yum", "install", "-y"] + packages,
            "pacman": ["sudo", "pacman", "-S", "--noconfirm"] + packages,
            "zypper": ["sudo", "zypper", "install", "-y"] + packages,
            "emerge": ["sudo", "emerge"] + packages,
            "apk": ["sudo", "apk", "add"] + packages,
            "xbps-install": ["sudo", "xbps-install", "-y"] + packages
        }
        
        return commands.get(self.pkg_manager)
    
    def get_package_names(self, generic_name):
        """Map generic package names to distro-specific names"""
        mappings = {
            "git": {
                "debian": "git",
                "fedora": "git",
                "arch": "git",
                "suse": "git",
                "gentoo": "dev-vcs/git",
                "alpine": "git",
                "void": "git"
            },
            "python3": {
                "debian": "python3 python3-venv python3-pip",
                "fedora": "python3 python3-pip",
                "arch": "python",
                "suse": "python3 python3-pip",
                "gentoo": "dev-lang/python",
                "alpine": "python3 py3-pip",
                "void": "python3 python3-pip"
            },
            "git-lfs": {
                "debian": "git-lfs",
                "fedora": "git-lfs",
                "arch": "git-lfs",
                "suse": "git-lfs",
                "gentoo": "dev-vcs/git-lfs",
                "alpine": "git-lfs",
                "void": "git-lfs"
            }
        }
        
        if generic_name in mappings:
            return mappings[generic_name].get(self.distro, generic_name)
        return generic_name

# ============================================================================
# UTILS
# ============================================================================

def run(cmd, check=True, quiet=False):
    """Run command"""
    try:
        if quiet:
            subprocess.run(cmd, check=check, shell=isinstance(cmd, str), 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, check=check, shell=isinstance(cmd, str))
        return True
    except subprocess.CalledProcessError as e:
        if not quiet:
            print(f"❌ Error: {e}")
        if check:
            return False
        return False

def log(msg, level="info"):
    """Simple logger"""
    icons = {"info": "🔵", "warn": "⚠️", "ok": "✅", "error": "❌"}
    print(f"{icons.get(level, '•')} {msg}")

def check_tool(cmd):
    """Check if command exists"""
    return shutil.which(cmd) is not None

# ============================================================================
# INSTALLER
# ============================================================================

class Installer:
    def __init__(self):
        self.distro_mgr = DistroManager()
        self.print_header()
        self.missing_deps = []
    
    def print_header(self):
        print("\n" + "=" * 60)
        print(" 3D ALL STARS LINUX EDITION - UNIVERSAL INSTALLER")
        print("=" * 60)
        print(f"\n📦 Detected distro: {self.distro_mgr.distro}")
        print(f"📦 Package manager: {self.distro_mgr.pkg_manager or 'None'}\n")
    
    def check_deps(self):
        """Check and offer to install dependencies"""
        log("Checking dependencies")
        
        deps = ['git', 'python3']
        self.missing_deps = [dep for dep in deps if not check_tool(dep)]
        
        if self.missing_deps:
            log(f"Missing dependencies: {', '.join(self.missing_deps)}", "warn")
            
            if self.distro_mgr.pkg_manager:
                response = input("\n❓ Install missing dependencies? (y/n): ").lower()
                if response == 'y':
                    return self.install_deps()
                else:
                    log("Cannot continue without dependencies", "error")
                    return False
            else:
                log("Cannot auto-install. Please install manually:", "error")
                for dep in self.missing_deps:
                    pkg_name = self.distro_mgr.get_package_names(dep)
                    print(f"   • {pkg_name}")
                return False
        
        log("All dependencies satisfied", "ok")
        return True
    
    def install_deps(self):
        """Install missing dependencies"""
        log("Installing dependencies...")
        
        all_packages = []
        for dep in self.missing_deps:
            pkg_names = self.distro_mgr.get_package_names(dep)
            all_packages.extend(pkg_names.split())
        
        cmd = self.distro_mgr.get_install_command(all_packages)
        if cmd:
            if run(cmd, check=False):
                log("Dependencies installed successfully", "ok")
                return True
            else:
                log("Failed to install dependencies", "error")
                return False
        return False
    
    def clone_repo(self):
        """Clone repository"""
        log("Cloning repository")
        
        if INSTALL_DIR.exists():
            log(f"Directory exists: {INSTALL_DIR}", "warn")
            response = input("❓ Remove and reinstall? (y/n): ").lower()
            if response == 'y':
                shutil.rmtree(INSTALL_DIR)
            else:
                log("Using existing directory", "info")
                return True
        
        if not run(["git", "clone", "--depth=1", REPO_URL, str(INSTALL_DIR)], check=False):
            log("Failed to clone repository", "error")
            return False
        
        os.chdir(INSTALL_DIR)
        
        # Try git-lfs if available (optional, won't fail if missing)
        if check_tool("git-lfs") or check_tool("git"):
            log("Setting up Git LFS (optional)...", "info")
            run(["git", "lfs", "install"], check=False, quiet=True)
            run(["git", "lfs", "pull"], check=False, quiet=True)
        
        return True
    
    def setup_python(self):
        """Setup Python environment"""
        log("Setting up Python environment")
        
        venv = INSTALL_DIR / ".venv"
        
        if not venv.exists():
            # Try python3 -m venv
            if not run([sys.executable, "-m", "venv", str(venv)], check=False):
                log("Failed to create virtual environment", "error")
                log("You may need to install python3-venv package", "warn")
                return False
        
        # Determine pip path
        pip = venv / "bin" / "pip"
        if not pip.exists():
            pip = venv / "bin" / "pip3"
        
        reqs = INSTALL_DIR / "requirements.txt"
        
        if reqs.exists() and pip.exists():
            log("Installing Python packages...")
            run([str(pip), "install", "-q", "--upgrade", "pip"], check=False, quiet=True)
            if not run([str(pip), "install", "-q", "-r", str(reqs)], check=False):
                log("Warning: Some Python packages may have failed to install", "warn")
        
        return True
    
    def setup_icon(self):
        """Download icon"""
        log("Setting up icon")
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            urllib.request.urlretrieve(ICON_URL, ICON)
            return True
        except Exception as e:
            log(f"Icon download failed: {e}", "warn")
            return False
    
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
        return True
    
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
        return True
    
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
                if script.exists():
                    script.chmod(script.stat().st_mode | 0o111)
        
        return True
    
    def refresh_desktop(self):
        """Refresh desktop database"""
        log("Refreshing desktop")
        
        run(f"update-desktop-database {APPS_DIR}", check=False, quiet=True)
        run(f"gtk-update-icon-cache {ICONS_DIR}", check=False, quiet=True)
        
        return True
    
    def run(self):
        """Run installation"""
        try:
            if not self.check_deps():
                sys.exit(1)
            
            if not self.clone_repo():
                sys.exit(1)
            
            if not self.setup_python():
                sys.exit(1)
            
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
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def print_success(self):
        """Print success message"""
        print("\n" + "=" * 60)
        print(" ✅ INSTALLATION COMPLETE!")
        print("=" * 60)
        print(f"\n📁 Installed: {INSTALL_DIR}")
        print("\n🎮 Launch:")
        print(f"   • Applications Menu → Super Mario 3D All Stars")
        print(f"   • Or run: {LAUNCHER}")
        print("\n💡 If icon doesn't appear:")
        print("   • Log out and back in")
        print(f"   • Or: update-desktop-database {APPS_DIR}")
        print("\n" + "=" * 60 + "\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    if os.geteuid() == 0:
        print("⚠️  Don't run this script as root/sudo!")
        print("   Dependencies will be installed with sudo when needed.\n")
        sys.exit(1)
    
    installer = Installer()
    installer.run()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
3D All Stars Linux Edition - Universal Multi-Distro Installer
Author: retired64
License: MIT

This installer handles:
- Multi-distro package management
- Git LFS setup and binary downloading
- Python virtual environment
- Desktop integration
- Executable permissions
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
                if "ubuntu" in content or "debian" in content or "mint" in content or "pop" in content:
                    return "debian"
                elif "fedora" in content or "rhel" in content or "centos" in content or "rocky" in content:
                    return "fedora"
                elif "arch" in content or "manjaro" in content or "endeavour" in content:
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
            "pacman": ["sudo", "pacman", "-S", "--noconfirm", "--needed"] + packages,
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
                "debian": ["git"],
                "fedora": ["git"],
                "arch": ["git"],
                "suse": ["git"],
                "gentoo": ["dev-vcs/git"],
                "alpine": ["git"],
                "void": ["git"]
            },
            "git-lfs": {
                "debian": ["git-lfs"],
                "fedora": ["git-lfs"],
                "arch": ["git-lfs"],
                "suse": ["git-lfs"],
                "gentoo": ["dev-vcs/git-lfs"],
                "alpine": ["git-lfs"],
                "void": ["git-lfs"]
            },
            "python3": {
                "debian": ["python3", "python3-venv", "python3-pip"],
                "fedora": ["python3", "python3-pip"],
                "arch": ["python", "python-pip"],
                "suse": ["python3", "python3-pip"],
                "gentoo": ["dev-lang/python"],
                "alpine": ["python3", "py3-pip"],
                "void": ["python3", "python3-pip"]
            }
        }
        
        if generic_name in mappings:
            return mappings[generic_name].get(self.distro, [generic_name])
        return [generic_name]

# ============================================================================
# UTILS
# ============================================================================

def run(cmd, check=True, quiet=False, capture=False):
    """Run command"""
    try:
        if capture:
            result = subprocess.run(cmd, check=check, shell=isinstance(cmd, str),
                                  capture_output=True, text=True)
            return result.stdout.strip()
        elif quiet:
            subprocess.run(cmd, check=check, shell=isinstance(cmd, str), 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(cmd, check=check, shell=isinstance(cmd, str))
        return True
    except subprocess.CalledProcessError as e:
        if not quiet and not capture:
            print(f"❌ Error: {e}")
        return False

def log(msg, level="info"):
    """Simple logger"""
    icons = {"info": "🔵", "warn": "⚠️", "ok": "✅", "error": "❌", "lfs": "📦"}
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
        print("\n" + "=" * 70)
        print("  3D ALL STARS LINUX EDITION - UNIVERSAL INSTALLER")
        print("=" * 70)
        print(f"\n📦 Detected: {self.distro_mgr.distro.capitalize()}")
        print(f"📦 Package Manager: {self.distro_mgr.pkg_manager or 'Manual installation required'}\n")
    
    def check_deps(self):
        """Check and offer to install dependencies"""
        log("Checking dependencies")
        
        # Essential dependencies
        essential = ['git', 'python3']
        self.missing_deps = [dep for dep in essential if not check_tool(dep)]
        
        # Check Git LFS separately
        has_lfs = check_tool("git-lfs")
        
        if self.missing_deps:
            log(f"Missing: {', '.join(self.missing_deps)}", "error")
            
            if self.distro_mgr.pkg_manager:
                response = input("\n❓ Install missing dependencies? (y/n): ").lower()
                if response == 'y':
                    if not self.install_deps(self.missing_deps):
                        return False
                else:
                    log("Cannot continue without dependencies", "error")
                    return False
            else:
                self.show_manual_install(self.missing_deps)
                return False
        
        # Handle Git LFS
        if not has_lfs:
            log("Git LFS not found (REQUIRED for binaries)", "warn")
            print("\n⚠️  IMPORTANT: This project uses Git LFS for emulator binaries.")
            print("   Without Git LFS, emulators will fail with 'version not found' errors.\n")
            
            if self.distro_mgr.pkg_manager:
                response = input("❓ Install Git LFS now? (HIGHLY RECOMMENDED) (y/n): ").lower()
                if response == 'y':
                    if not self.install_deps(['git-lfs']):
                        log("Git LFS installation failed. You can install it later manually.", "warn")
                else:
                    log("Continuing without Git LFS (binaries won't download)", "warn")
            else:
                self.show_manual_install(['git-lfs'])
        else:
            log("Git LFS found", "ok")
        
        log("Dependencies check complete", "ok")
        return True
    
    def install_deps(self, deps):
        """Install missing dependencies"""
        log(f"Installing: {', '.join(deps)}...")
        
        all_packages = []
        for dep in deps:
            pkg_names = self.distro_mgr.get_package_names(dep)
            all_packages.extend(pkg_names)
        
        # Remove duplicates
        all_packages = list(set(all_packages))
        
        cmd = self.distro_mgr.get_install_command(all_packages)
        if cmd:
            if run(cmd, check=False):
                log("Packages installed successfully", "ok")
                return True
            else:
                log("Package installation failed", "error")
                return False
        return False
    
    def show_manual_install(self, deps):
        """Show manual installation instructions"""
        log("Please install these packages manually:", "error")
        for dep in deps:
            pkg_names = self.distro_mgr.get_package_names(dep)
            print(f"   • {dep}: {' '.join(pkg_names)}")
        
        print("\n📖 Installation examples:")
        print("   Ubuntu/Debian: sudo apt install git git-lfs python3 python3-venv")
        print("   Fedora:        sudo dnf install git git-lfs python3 python3-pip")
        print("   Arch:          sudo pacman -S git git-lfs python python-pip")
        print("   openSUSE:      sudo zypper install git git-lfs python3 python3-pip")
    
    def clone_repo(self):
        """Clone repository"""
        log("Cloning repository")
        
        if INSTALL_DIR.exists():
            log(f"Directory exists: {INSTALL_DIR}", "warn")
            response = input("❓ Remove and reinstall? (y/n): ").lower()
            if response == 'y':
                log("Removing old installation...")
                shutil.rmtree(INSTALL_DIR)
            else:
                log("Using existing directory", "info")
                os.chdir(INSTALL_DIR)
                return True
        
        log("Cloning (this may take a moment)...")
        if not run(["git", "clone", "--depth=1", REPO_URL, str(INSTALL_DIR)], check=False):
            log("Failed to clone repository", "error")
            return False
        
        os.chdir(INSTALL_DIR)
        log("Repository cloned successfully", "ok")
        return True
    
    def setup_git_lfs(self):
        """Setup Git LFS and download binaries"""
        if not check_tool("git-lfs"):
            log("Git LFS not available - skipping binary download", "warn")
            print("\n⚠️  EMULATORS WON'T WORK WITHOUT GIT LFS!")
            print("   Install git-lfs and run: cd ~/3D-All-Stars-Linux-EDITION && git lfs pull\n")
            return False
        
        log("Setting up Git LFS...", "lfs")
        
        # Initialize LFS
        if not run(["git", "lfs", "install"], check=False, quiet=True):
            log("Git LFS init failed", "warn")
            return False
        
        # Pull LFS files
        log("Downloading emulator binaries (this may take several minutes)...", "lfs")
        if not run(["git", "lfs", "pull"], check=False):
            log("Git LFS pull failed - binaries may be incomplete", "warn")
            return False
        
        log("Binaries downloaded successfully", "ok")
        return True
    
    def setup_python(self):
        """Setup Python environment"""
        log("Setting up Python environment")
        
        venv = INSTALL_DIR / ".venv"
        
        if not venv.exists():
            log("Creating virtual environment...")
            if not run([sys.executable, "-m", "venv", str(venv)], check=False):
                log("Failed to create virtual environment", "error")
                log("Install python3-venv package for your distro", "warn")
                return False
        
        # Determine pip path
        pip = venv / "bin" / "pip"
        if not pip.exists():
            pip = venv / "bin" / "pip3"
        
        if not pip.exists():
            log("Virtual environment created but pip not found", "error")
            return False
        
        reqs = INSTALL_DIR / "requirements.txt"
        
        if reqs.exists():
            log("Installing Python dependencies...")
            run([str(pip), "install", "-q", "--upgrade", "pip"], check=False, quiet=True)
            if not run([str(pip), "install", "-q", "-r", str(reqs)], check=False):
                log("Some Python packages failed to install", "warn")
        
        log("Python environment ready", "ok")
        return True
    
    def setup_icon(self):
        """Download icon"""
        log("Setting up icon")
        ICONS_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            urllib.request.urlretrieve(ICON_URL, ICON)
            log("Icon downloaded", "ok")
            return True
        except Exception as e:
            log(f"Icon download failed: {e}", "warn")
            return False
    
    def create_launcher(self):
        """Create launcher script"""
        log("Creating launcher")
        
        script = f"""#!/bin/bash
# 3D All Stars Linux Edition Launcher
cd "{INSTALL_DIR}" || exit 1
source .venv/bin/activate
python3 main.py "$@"
"""
        
        LAUNCHER.write_text(script)
        LAUNCHER.chmod(0o755)
        log("Launcher created", "ok")
        return True
    
    def create_desktop(self):
        """Create desktop entry"""
        log("Creating desktop entry")
        APPS_DIR.mkdir(parents=True, exist_ok=True)
        
        icon_path = ICON if ICON.exists() else ""
        
        entry = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Super Mario 3D All Stars
Comment=3D All Stars Linux Edition - Console-like Gaming Experience
Icon={icon_path}
Exec={LAUNCHER}
Path={INSTALL_DIR}
Terminal=false
Categories=Game;Emulator;
Keywords=mario;dolphin;emulator;nintendo;
"""
        
        DESKTOP.write_text(entry)
        DESKTOP.chmod(0o644)
        log("Desktop entry created", "ok")
        return True
    
    def set_permissions(self):
        """Set executable permissions for emulators and game scripts"""
        log("Setting executable permissions")
        
        executables = [
            "dolphin-emulator/dolphin-emu",
            "3ds/azahar.AppImage",
            "nds/melonDS",
            "main.py",
            "game_editor.py"
        ]
        
        for exe in executables:
            path = INSTALL_DIR / exe
            if path.exists():
                path.chmod(path.stat().st_mode | 0o111)
        
        # Game run scripts
        games = INSTALL_DIR / "games"
        if games.exists():
            for script in games.glob("*/run"):
                if script.exists():
                    script.chmod(script.stat().st_mode | 0o111)
        
        log("Permissions set", "ok")
        return True
    
    def refresh_desktop(self):
        """Refresh desktop database"""
        log("Refreshing desktop database")
        
        run(f"update-desktop-database {APPS_DIR}", check=False, quiet=True)
        run(f"gtk-update-icon-cache {ICONS_DIR}", check=False, quiet=True)
        
        return True
    
    def verify_installation(self):
        """Verify critical files exist"""
        log("Verifying installation")
        
        critical_files = [
            "main.py",
            "requirements.txt",
            "games.json"
        ]
        
        missing = []
        for file in critical_files:
            if not (INSTALL_DIR / file).exists():
                missing.append(file)
        
        if missing:
            log(f"Missing files: {', '.join(missing)}", "error")
            return False
        
        # Check if binaries are actual files (not LFS pointers)
        dolphin = INSTALL_DIR / "dolphin-emulator" / "dolphin-emu"
        if dolphin.exists():
            size = dolphin.stat().st_size
            if size < 1000000:  # Less than 1MB = probably LFS pointer
                log("WARNING: Emulator binaries may not be downloaded (Git LFS issue)", "warn")
                print("   Run: cd ~/3D-All-Stars-Linux-EDITION && git lfs pull")
        
        log("Installation verified", "ok")
        return True
    
    def run(self):
        """Run installation"""
        try:
            if not self.check_deps():
                sys.exit(1)
            
            if not self.clone_repo():
                sys.exit(1)
            
            lfs_ok = self.setup_git_lfs()
            
            if not self.setup_python():
                sys.exit(1)
            
            self.setup_icon()
            self.create_launcher()
            self.create_desktop()
            self.set_permissions()
            self.refresh_desktop()
            self.verify_installation()
            
            self.print_success(lfs_ok)
            
        except KeyboardInterrupt:
            log("\n\nInstallation cancelled by user", "warn")
            sys.exit(130)
        except Exception as e:
            log(f"\nInstallation failed: {e}", "error")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    def print_success(self, lfs_ok):
        """Print success message"""
        print("\n" + "=" * 70)
        print("  ✅ INSTALLATION COMPLETE!")
        print("=" * 70)
        print(f"\n📁 Installed to: {INSTALL_DIR}")
        
        if not lfs_ok:
            print("\n⚠️  WARNING: Git LFS binaries may be incomplete!")
            print("   To download emulator binaries, run:")
            print(f"   cd {INSTALL_DIR}")
            print("   git lfs install && git lfs pull")
        
        print("\n🎮 How to Launch:")
        print("   • Applications Menu → 'Super Mario 3D All Stars'")
        print(f"   • Or run: {LAUNCHER}")
        print(f"   • Or run: cd {INSTALL_DIR} && python3 main.py")
        
        print("\n📝 Before Playing:")
        print("   1. Place your ROMs in the game folders (see README)")
        print("   2. Configure emulator controls:")
        print("      • Dolphin: Run dolphin-emulator/dolphin-emu directly")
        print("      • 3DS: Run 3ds/azahar.AppImage directly")
        print("      • NDS: Run nds/melonDS directly")
        
        print("\n🎨 Add New Games:")
        print(f"   python3 {INSTALL_DIR}/game_editor.py")
        
        print("\n💡 Troubleshooting:")
        print("   • If icon doesn't appear: Log out and back in")
        print("   • Emulator won't launch: Check Git LFS pulled binaries")
        print("   • Controls not working: Configure emulator settings first")
        
        print("\n📖 Full Documentation:")
        print("   https://github.com/retired64/3D-All-Stars-Linux-EDITION")
        
        print("\n" + "=" * 70 + "\n")

# ============================================================================
# MAIN
# ============================================================================

def main():
    if os.geteuid() == 0:
        print("\n⚠️  Don't run this script as root/sudo!")
        print("   The installer will request sudo only when needed.\n")
        sys.exit(1)
    
    installer = Installer()
    installer.run()

if __name__ == "__main__":
    main()

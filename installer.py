#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3D All Stars Linux Edition - Auto-Installer
Author: retired64
Version: 3.0.0
License: MIT

Enterprise-grade installer with dual-source fallback system and comprehensive error handling.
"""

import os
import sys
import subprocess
import shutil
import urllib.request
import zipfile
import importlib.util
import re
import logging
from pathlib import Path
from typing import Optional, Tuple
from contextlib import contextmanager
from enum import Enum


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Centralized configuration management."""
    REPO_URL = "https://github.com/retired64/3D-All-Stars-Linux-EDITION.git"
    REPO_NAME = "3D-All-Stars-Linux-EDITION"
    ICON_URL = "https://raw.githubusercontent.com/retired64/3D-All-Stars-Linux-EDITION/main/src/img/icon.png"
    
    # Dual source for assets with automatic fallback
    MEGA_ASSETS_URL = "https://mega.nz/file/qc1iCJzI#xS6NSL1d8-ro8a3xRRbQoNT1IWgo1XMf4ANesjJEuL4"
    GDRIVE_ASSETS_URL = "https://drive.google.com/file/d/1C7EOTaTG1NhdvzkG1GSmqXMILaIAIC8I/view?usp=sharing"
    ASSETS_FILENAME = "assets.zip"
    
    # Paths
    HOME_DIR = Path.home()
    INSTALL_DIR = HOME_DIR / REPO_NAME
    ASSETS_DIR = INSTALL_DIR / "assets"
    LOCAL_SHARE = HOME_DIR / ".local" / "share"
    ICONS_DIR = LOCAL_SHARE / "icons"
    APPLICATIONS_DIR = LOCAL_SHARE / "applications"
    LAUNCHER_SCRIPT = INSTALL_DIR / "launcher.sh"
    DESKTOP_FILE = APPLICATIONS_DIR / "3d-all-stars.desktop"
    ICON_DEST = ICONS_DIR / "3d-all-stars.png"
    
    # Validation
    MIN_ASSETS_SIZE = 1024 * 1024  # 1MB minimum
    REQUIRED_EXECUTABLES = [
        "dolphin-emulator/dolphin-emu",
        "3ds/azahar.AppImage",
        "nds/melonDS",
        "main.py"
    ]
    
    # Emulator validation commands (emulator_path: version_flag)
    EMULATOR_VERSION_FLAGS = {
        "dolphin-emulator/dolphin-emu": "--version",
        "3ds/azahar.AppImage": "--version",
        "nds/melonDS": "--version"  # Note: melonDS uses --version but exits with error
    }


class DownloadSource(Enum):
    """Asset download source enumeration."""
    MEGA = "MEGA"
    GDRIVE = "Google Drive"
    MANUAL = "Manual"


class InstallationError(Exception):
    """Custom exception for installation failures."""
    pass


# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging() -> logging.Logger:
    """Configure structured logging with color support."""
    logger = logging.getLogger("3D-All-Stars-Installer")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # Color formatting for terminals
    class ColorFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[34m',     # Blue
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
            'RESET': '\033[0m'
        }
        
        def format(self, record):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
            return super().format(record)
    
    formatter = ColorFormatter('🔵 [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


logger = setup_logging()


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================

@contextmanager
def safe_chdir(path: Path):
    """Context manager for safe directory changes."""
    original = Path.cwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)


@contextmanager
def temporary_file(path: Path):
    """Context manager for temporary file cleanup."""
    try:
        yield path
    finally:
        if path.exists():
            try:
                path.unlink()
            except OSError as e:
                logger.warning(f"Could not remove temporary file {path}: {e}")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def run_command(
    cmd: list,
    check: bool = True,
    capture: bool = False,
    timeout: int = 300
) -> Tuple[int, str, str]:
    """
    Execute shell command with comprehensive error handling.
    
    Args:
        cmd: Command as list of strings
        check: Raise exception on non-zero exit
        capture: Capture stdout/stderr
        timeout: Command timeout in seconds
    
    Returns:
        Tuple of (returncode, stdout, stderr)
    """
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout if capture else "", result.stderr if capture else ""
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout}s: {' '.join(cmd)}")
        raise InstallationError(f"Command timeout: {e}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with code {e.returncode}: {' '.join(cmd)}")
        if not check:
            return e.returncode, "", str(e)
        raise InstallationError(f"Command execution failed: {e}")
    except FileNotFoundError as e:
        logger.error(f"Command not found: {cmd[0]}")
        raise InstallationError(f"Missing system tool: {cmd[0]}")


def check_disk_space(path: Path, required_gb: float = 3.0) -> bool:
    """Verify sufficient disk space is available."""
    try:
        stat = shutil.disk_usage(path)
        available_gb = stat.free / (1024 ** 3)
        if available_gb < required_gb:
            logger.warning(f"Low disk space: {available_gb:.1f}GB available, {required_gb}GB recommended")
            return False
        return True
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Don't block installation


def validate_zip_file(zip_path: Path) -> bool:
    """Validate ZIP file integrity."""
    if not zip_path.exists():
        return False
    
    if zip_path.stat().st_size < Config.MIN_ASSETS_SIZE:
        logger.error(f"Assets file too small: {zip_path.stat().st_size} bytes")
        return False
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Test ZIP integrity
            corrupt = zf.testzip()
            if corrupt:
                logger.error(f"Corrupted file in ZIP: {corrupt}")
                return False
            
            # Verify it contains files
            if not zf.namelist():
                logger.error("ZIP file is empty")
                return False
                
        return True
    except zipfile.BadZipFile:
        logger.error("Invalid or corrupted ZIP file")
        return False
    except Exception as e:
        logger.error(f"ZIP validation failed: {e}")
        return False


# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

class DependencyChecker:
    """System dependency verification."""
    
    REQUIRED_SYSTEM_PACKAGES = {
        'git': 'sudo apt install git',
        'python3': 'sudo apt install python3'
    }
    
    OPTIONAL_PACKAGES = {
        'git-lfs': 'sudo apt install git-lfs && git lfs install'
    }
    
    @staticmethod
    def check_system_dependencies() -> bool:
        """Verify all required system tools are installed."""
        logger.info("Checking system dependencies")
        missing = []
        
        for cmd, install_hint in DependencyChecker.REQUIRED_SYSTEM_PACKAGES.items():
            if not shutil.which(cmd):
                logger.error(f"❌ Missing required tool: {cmd}")
                logger.error(f"   Install with: {install_hint}")
                missing.append(cmd)
        
        if missing:
            raise InstallationError(f"Missing required dependencies: {', '.join(missing)}")
        
        # Check optional but recommended
        for cmd, install_hint in DependencyChecker.OPTIONAL_PACKAGES.items():
            if not shutil.which(cmd):
                logger.warning(f"⚠️  Recommended tool not found: {cmd}")
                logger.warning(f"   Install with: {install_hint}")
                response = input("   Continue without it? (y/N): ").strip().lower()
                if response != 'y':
                    raise InstallationError("Installation cancelled by user")
        
        # Verify Git LFS is initialized
        try:
            result = subprocess.run(['git', 'lfs', 'version'], capture_output=True)
            if result.returncode != 0:
                logger.warning("Git LFS not initialized")
        except Exception:
            pass
        
        return True
    
    @staticmethod
    def install_python_package(package: str, import_name: Optional[str] = None) -> bool:
        """Install Python package if not present."""
        import_name = import_name or package
        
        if importlib.util.find_spec(import_name):
            return True
        
        logger.info(f"Installing Python package: {package}")
        try:
            run_command([sys.executable, "-m", "pip", "install", "--quiet", package])
            return True
        except InstallationError as e:
            logger.error(f"Failed to install {package}: {e}")
            return False


# ============================================================================
# DOWNLOAD STRATEGIES
# ============================================================================

class AssetDownloader:
    """Multi-source asset download manager with fallback chain."""
    
    def __init__(self, config: Config):
        self.config = config
        self.download_source = None
    
    def download(self) -> Tuple[bool, Optional[Path]]:
        """
        Execute download chain with automatic fallback.
        
        Returns:
            (success: bool, file_path: Optional[Path])
        """
        logger.info("Starting asset download process")
        
        # Ensure target directory exists
        self.config.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        dest_file = self.config.INSTALL_DIR / self.config.ASSETS_FILENAME
        
        # Try MEGA first
        if self._download_from_mega(dest_file):
            self.download_source = DownloadSource.MEGA
            return True, dest_file
        
        # Fallback to Google Drive
        if self._download_from_gdrive(dest_file):
            self.download_source = DownloadSource.GDRIVE
            return True, dest_file
        
        # Both failed
        self.download_source = DownloadSource.MANUAL
        logger.error("All automatic download sources failed")
        return False, None
    
    def _download_from_mega(self, dest: Path) -> bool:
        """Attempt download from MEGA."""
        logger.info("Trying primary source: MEGA")
        
        try:
            # Install mega.py if needed
            if not DependencyChecker.install_python_package("mega.py", "mega"):
                return False
            
            from mega import Mega
            
            mega = Mega()
            m = mega.login()
            
            logger.info("Downloading from MEGA (this may take a few minutes)...")
            filename = m.download_url(
                self.config.MEGA_ASSETS_URL,
                dest_path=str(self.config.INSTALL_DIR)
            )
            
            # Rename to expected filename
            downloaded = self.config.INSTALL_DIR / filename
            if downloaded.exists() and downloaded != dest:
                downloaded.rename(dest)
            
            if validate_zip_file(dest):
                logger.info("✅ Successfully downloaded from MEGA")
                return True
            else:
                logger.warning("Downloaded file failed validation")
                return False
                
        except ImportError as e:
            logger.warning(f"MEGA library unavailable: {e}")
            return False
        except Exception as e:
            logger.warning(f"MEGA download failed: {type(e).__name__}: {str(e)[:100]}")
            return False
    
    def _download_from_gdrive(self, dest: Path) -> bool:
        """Attempt download from Google Drive."""
        logger.info("Trying fallback source: Google Drive")
        
        try:
            file_id = self._extract_gdrive_id(self.config.GDRIVE_ASSETS_URL)
            if not file_id:
                logger.warning("Could not extract Google Drive file ID")
                return False
            
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # Handle Google Drive's virus scan confirmation for larger files
            opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
            urllib.request.install_opener(opener)
            
            logger.info("Downloading from Google Drive...")
            
            # First request to check for confirmation
            with urllib.request.urlopen(download_url, timeout=30) as response:
                content = response.read(131072)  # Read first 128KB
                
                # Check if confirmation is needed
                if b'id="download-form"' in content or b'confirm=' in content:
                    confirm_match = re.search(rb'confirm=([^&"]+)', content)
                    if confirm_match:
                        confirm_token = confirm_match.group(1).decode()
                        download_url += f"&confirm={confirm_token}"
                        logger.info("Handling virus scan confirmation...")
            
            # Actual download
            urllib.request.urlretrieve(download_url, dest)
            
            if validate_zip_file(dest):
                logger.info("✅ Successfully downloaded from Google Drive")
                return True
            else:
                logger.warning("Downloaded file failed validation")
                return False
                
        except urllib.error.URLError as e:
            logger.warning(f"Network error downloading from GDrive: {e}")
            return False
        except Exception as e:
            logger.warning(f"GDrive download failed: {type(e).__name__}: {str(e)[:100]}")
            return False
    
    @staticmethod
    def _extract_gdrive_id(url: str) -> Optional[str]:
        """Extract file ID from various Google Drive URL formats."""
        patterns = [
            r'id=([0-9A-Za-z_-]{25,})',
            r'/file/d/([0-9A-Za-z_-]{25,})',
            r'/d/([0-9A-Za-z_-]{25,})',
            r'folders/([0-9A-Za-z_-]{25,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None


# ============================================================================
# INSTALLATION ORCHESTRATOR
# ============================================================================

class Installer:
    """Main installation orchestrator."""
    
    def __init__(self):
        self.config = Config()
        self.assets_installed = False
        self.emulator_status = None
    
    def run(self):
        """Execute complete installation workflow."""
        try:
            self._print_header()
            
            # Pre-flight checks
            check_disk_space(self.config.HOME_DIR)
            DependencyChecker.check_system_dependencies()
            
            # Installation phases
            self._setup_repository()
            self._download_and_extract_assets()
            self._setup_python_environment()
            self._setup_system_integration()
            self._set_permissions()
            self.emulator_status = self._validate_emulators()
            self._refresh_desktop_database()
            
            self._print_success()
            
        except InstallationError as e:
            logger.error(f"Installation failed: {e}")
            self._print_failure(str(e))
            sys.exit(1)
        except KeyboardInterrupt:
            logger.warning("\nInstallation cancelled by user")
            sys.exit(130)
        except Exception as e:
            logger.critical(f"Unexpected error: {type(e).__name__}: {e}")
            self._print_failure(f"Unexpected error: {e}")
            sys.exit(1)
    
    def _setup_repository(self):
        """Clone repository and fetch LFS objects."""
        logger.info("Setting up repository")
        
        if self.config.INSTALL_DIR.exists():
            logger.info(f"Directory {self.config.INSTALL_DIR} already exists, skipping clone")
        else:
            logger.info(f"Cloning repository to {self.config.INSTALL_DIR}")
            run_command([
                "git", "clone",
                "--depth=1",
                self.config.REPO_URL,
                str(self.config.INSTALL_DIR)
            ])
        
        with safe_chdir(self.config.INSTALL_DIR):
            logger.info("Initializing Git LFS")
            run_command(["git", "lfs", "install"], check=False)
            
            logger.info("Fetching large binary files")
            run_command(["git", "lfs", "pull"])
    
    def _download_and_extract_assets(self):
        """Download assets from available source and extract."""
        logger.info("Processing game assets")
        
        downloader = AssetDownloader(self.config)
        success, zip_path = downloader.download()
        
        if not success or not zip_path:
            self.assets_installed = False
            logger.warning("Could not download assets automatically")
            return
        
        # Extract with validation
        try:
            with temporary_file(zip_path):
                logger.info(f"Extracting assets to {self.config.ASSETS_DIR}")
                
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(self.config.ASSETS_DIR)
                
                logger.info(f"✅ Assets extracted successfully from {downloader.download_source.value}")
                self.assets_installed = True
                
        except zipfile.BadZipFile as e:
            logger.error(f"Corrupted ZIP file: {e}")
            self.assets_installed = False
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            self.assets_installed = False
    
    def _setup_python_environment(self):
        """Create virtual environment and install dependencies."""
        logger.info("Configuring Python environment")
        
        venv_path = self.config.INSTALL_DIR / ".venv"
        
        if not venv_path.exists():
            logger.info("Creating virtual environment")
            run_command([sys.executable, "-m", "venv", str(venv_path)])
        
        pip_executable = venv_path / "bin" / "pip"
        requirements = self.config.INSTALL_DIR / "requirements.txt"
        
        if requirements.exists():
            logger.info("Installing Python dependencies")
            run_command([
                str(pip_executable),
                "install",
                "--quiet",
                "--upgrade",
                "pip"
            ])
            run_command([
                str(pip_executable),
                "install",
                "-r",
                str(requirements)
            ])
        else:
            logger.warning("requirements.txt not found, skipping Python dependencies")
    
    def _setup_system_integration(self):
        """Create launcher script and desktop entry."""
        logger.info("Integrating with system")
        
        # Download/copy icon
        self._setup_icon()
        
        # Create launcher script
        self._create_launcher_script()
        
        # Create desktop entry
        self._create_desktop_entry()
    
    def _setup_icon(self):
        """Download or copy application icon."""
        self.config.ICONS_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info("Downloading application icon")
            urllib.request.urlretrieve(self.config.ICON_URL, self.config.ICON_DEST)
        except Exception as e:
            logger.warning(f"Could not download icon: {e}, trying local copy")
            local_icon = self.config.INSTALL_DIR / "src" / "img" / "icon.png"
            if local_icon.exists():
                shutil.copy2(local_icon, self.config.ICON_DEST)
            else:
                logger.warning("No icon available")
    
    def _create_launcher_script(self):
        """Generate shell launcher script."""
        script_content = f"""#!/usr/bin/env bash
# 3D All Stars Linux Edition Launcher
# Auto-generated by installer

set -e

cd "{self.config.INSTALL_DIR}"
source .venv/bin/activate
exec python3 main.py "$@"
"""
        
        self.config.LAUNCHER_SCRIPT.write_text(script_content)
        self.config.LAUNCHER_SCRIPT.chmod(0o755)
        logger.info(f"Created launcher script: {self.config.LAUNCHER_SCRIPT}")
    
    def _create_desktop_entry(self):
        """Generate XDG desktop entry."""
        self.config.APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Super Mario 3D All Stars
GenericName=Game Collection
Comment=3D All Stars Linux Edition by retired64
Icon={self.config.ICON_DEST}
Exec={self.config.LAUNCHER_SCRIPT}
Path={self.config.INSTALL_DIR}
Terminal=false
Categories=Game;Emulator;
Keywords=mario;nintendo;emulator;
StartupNotify=true
StartupWMClass=3d-all-stars
"""
        
        self.config.DESKTOP_FILE.write_text(desktop_content)
        self.config.DESKTOP_FILE.chmod(0o644)
        logger.info(f"Created desktop entry: {self.config.DESKTOP_FILE}")
    
    def _set_permissions(self):
        """Set executable permissions on required files."""
        logger.info("Setting executable permissions")
        
        executables = [
            self.config.INSTALL_DIR / exe
            for exe in self.config.REQUIRED_EXECUTABLES
        ]
        
        # Add game run scripts
        games_dir = self.config.INSTALL_DIR / "games"
        if games_dir.exists():
            executables.extend(games_dir.glob("*/run"))
        
        for exe in executables:
            if exe.exists():
                try:
                    exe.chmod(exe.stat().st_mode | 0o111)  # Add +x for all
                except Exception as e:
                    logger.warning(f"Could not set permissions on {exe}: {e}")
    
    def _validate_emulators(self):
        """Verify emulator binaries are functional."""
        logger.info("Validating emulator binaries")
        
        validation_results = {
            'working': [],
            'broken': [],
            'untested': []
        }
        
        for exe_rel_path, version_flag in self.config.EMULATOR_VERSION_FLAGS.items():
            exe_path = self.config.INSTALL_DIR / exe_rel_path
            
            if not exe_path.exists():
                validation_results['untested'].append(exe_path.name)
                logger.warning(f"⚠️  Emulator not found: {exe_path.name}")
                continue
            
            try:
                # Run version check with timeout
                result = subprocess.run(
                    [str(exe_path), version_flag],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                # Parse output
                output = result.stdout + result.stderr
                
                # Special handling for melonDS (exits with code 1 on --version)
                if exe_path.name == "melonDS":
                    if "melonDS" in output and any(v in output for v in ["1.0", "1.1", "1.2"]):
                        version_match = re.search(r'melonDS\s+([\d.]+)', output)
                        version = version_match.group(1) if version_match else "unknown"
                        validation_results['working'].append(f"{exe_path.name} v{version}")
                        logger.info(f"✅ {exe_path.name} validated (v{version})")
                    else:
                        validation_results['broken'].append(exe_path.name)
                        logger.warning(f"⚠️  {exe_path.name} validation unclear")
                
                # Standard validation (returncode 0)
                elif result.returncode == 0:
                    # Extract version from output
                    version_match = re.search(r'(?:version|v\.?|)\s*([\d.]+)', output, re.IGNORECASE)
                    version = version_match.group(1) if version_match else "unknown"
                    
                    validation_results['working'].append(f"{exe_path.name} v{version}")
                    logger.info(f"✅ {exe_path.name} validated (v{version})")
                
                else:
                    validation_results['broken'].append(exe_path.name)
                    logger.warning(f"⚠️  {exe_path.name} returned non-zero exit code")
                    
            except subprocess.TimeoutExpired:
                validation_results['broken'].append(exe_path.name)
                logger.warning(f"⚠️  {exe_path.name} validation timed out (may hang on startup)")
                
            except FileNotFoundError:
                validation_results['untested'].append(exe_path.name)
                logger.warning(f"⚠️  {exe_path.name} missing required dependencies")
                
            except Exception as e:
                validation_results['untested'].append(exe_path.name)
                logger.warning(f"⚠️  Could not validate {exe_path.name}: {type(e).__name__}")
        
        # Summary
        if validation_results['working']:
            logger.info(f"Working emulators: {', '.join(validation_results['working'])}")
        
        if validation_results['broken']:
            logger.warning(f"Potentially broken emulators: {', '.join(validation_results['broken'])}")
            logger.warning("These emulators may need system dependencies installed")
        
        if validation_results['untested']:
            logger.info(f"Untested: {', '.join(validation_results['untested'])}")
        
        return validation_results
    
    def _refresh_desktop_database(self):
        """Update system desktop database."""
        logger.info("Refreshing desktop database")
        
        try:
            run_command(
                ["update-desktop-database", str(self.config.APPLICATIONS_DIR)],
                check=False,
                timeout=10
            )
        except Exception as e:
            logger.warning(f"Could not update desktop database: {e}")
        
        # Try to refresh icon cache
        try:
            run_command(
                ["gtk-update-icon-cache", str(self.config.ICONS_DIR)],
                check=False,
                timeout=10
            )
        except Exception:
            pass  # Not critical
    
    def _print_header(self):
        """Display installation header."""
        print("\n" + "=" * 70)
        print("   3D ALL STARS LINUX EDITION - AUTOMATED INSTALLER")
        print("   Author: retired64")
        print("   Version: 3.0.0")
        print("=" * 70 + "\n")
    
    def _print_success(self):
        """Display success message."""
        print("\n" + "=" * 70)
        print("   ✅ INSTALLATION COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print(f"\nInstalled to: {self.config.INSTALL_DIR}")
        
        # Assets status
        if self.assets_installed:
            print("\n✅ All assets downloaded and installed")
        else:
            print("\n⚠️  WARNING: Assets were not installed automatically")
            print("\nManual installation required:")
            print(f"  1. Download assets from:")
            print(f"     • MEGA: {self.config.MEGA_ASSETS_URL}")
            print(f"     • Google Drive: {self.config.GDRIVE_ASSETS_URL}")
            print(f"  2. Extract the ZIP file to: {self.config.ASSETS_DIR}")
        
        # Emulator validation status
        if self.emulator_status:
            print("\n📦 Emulator Status:")
            if self.emulator_status['working']:
                print(f"   ✅ Working: {', '.join(self.emulator_status['working'])}")
            if self.emulator_status['broken']:
                print(f"   ⚠️  May need dependencies: {', '.join(self.emulator_status['broken'])}")
                print("      Try: sudo apt install libsdl2-2.0-0 libgl1 libqt5widgets5")
            if self.emulator_status['untested']:
                print(f"   ℹ️  Not validated: {', '.join(self.emulator_status['untested'])}")
        
        print("\n🎮 Launch the game:")
        print("   • From Applications Menu → Super Mario 3D All Stars")
        print(f"   • Or run: {self.config.LAUNCHER_SCRIPT}")
        
        print("\nIf the icon doesn't appear immediately:")
        print("  • Log out and log back in")
        print("  • Or run: update-desktop-database ~/.local/share/applications")
        print("\n" + "=" * 70 + "\n")
    
    def _print_failure(self, error: str):
        """Display failure message."""
        print("\n" + "=" * 70)
        print("   ❌ INSTALLATION FAILED")
        print("=" * 70)
        print(f"\nError: {error}")
        print("\nPlease check:")
        print("  • You have a stable internet connection")
        print("  • Git and Git LFS are properly installed")
        print("  • You have sufficient disk space (~3GB)")
        print("\nFor support, visit:")
        print("  https://github.com/retired64/3D-All-Stars-Linux-EDITION/issues")
        print("\n" + "=" * 70 + "\n")


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Application entry point."""
    installer = Installer()
    installer.run()


if __name__ == "__main__":
    main()
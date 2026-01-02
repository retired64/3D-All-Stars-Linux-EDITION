<div align="center">
  <img src="src/img/logo.png" alt="Banner 3D All Stars Linux EDITION" width="100%">
  <img src="src/img/showcase.webp" alt="Show Case Launcher" width="100%">
  <br><br>
  
  <a href="https://github.com/retired64/3D-All-Stars-Linux-EDITION/fork">
    <img src="src/img/fork.png" alt="Fork this repository" width="140" />
  </a>

https://github.com/user-attachments/assets/81190d8c-2ccf-4ec2-9680-7ea807dc44db


    
  ![GitHub forks](https://img.shields.io/github/forks/retired64/3D-All-Stars-Linux-EDITION?style=social)
  ![GitHub stars](https://img.shields.io/github/stars/retired64/3D-All-Stars-Linux-EDITION?style=social)
  ![Version](https://img.shields.io/badge/version-1.0--prerelease-blue)
  ![Platform](https://img.shields.io/badge/platform-Linux-orange)
  ![License](https://img.shields.io/badge/license-MIT-green)
  
</div>

## About This Project

Welcome to 3D All Stars Linux EDITION! This program is designed to give you a console-like "Plug & Play" experience with gamepad support, ambient music, and a smooth interface.
**Version:** 1.0 (Pre-release)  
**Platform:** Linux (Ubuntu/Debian tested)  
**Release Page:** [Download Latest Release](https://github.com/retired64/3D-All-Stars-Linux-EDITION/releases)

<div align="center">
  <a href="https://mega.nz/file/qc1iCJzI#xS6NSL1d8-ro8a3xRRbQoNT1IWgo1XMf4ANesjJEuL4" target="_blank">
    <img src="src/img/dl.png" alt="assets folder" width="400"/>
  </a>
</div>

<div align="center">
  <img src="src/img/potential.png" alt="Potential" width="400"/>
</div>

This isn't just a game menu; it's a **unified command center**.

* **Full Compatibility:** Thanks to the `run` file system, you can launch virtually anything: Emulators (Dolphin, Citra, Desmume), native Linux games, or even custom scripts.
* **Immersive Experience:** Includes background video loading, individual sound effects per game, and optimized navigation.
* **Portability:** If you maintain the folder structure, you can take your collection to any PC with Ubuntu/Debian or other Linux distributions (not yet tested on all distros).

---

## Who Is This For?

This project is ideal for:
- Linux users who want a console-like gaming experience
- Users comfortable with basic file management
- Players who prefer gamepad-first navigation

<div align="center">
  <img src="src/img/configure.png" alt="Configure" width="400"/>
</div>

For the Launcher to work, you need to place your files following the structure the program expects.

### 1. The Importance of the `run` File

Each game inside the `games/game_name/` folder has a file called `run`.
**What's it for?** It's a "bridge". Instead of the Launcher trying to guess how to open each emulator, the Launcher simply executes `run`, and this script handles opening the emulator with the correct configuration and ROM.

**Example of what a `run` file should look like (for Dolphin/GameCube):**

```bash
#!/bin/sh
cd "$(dirname "$0")" || exit 1
# Calls the emulator and loads the ISO you place in that folder
../../dolphin-emulator/dolphin-emu -b -e MyGame.iso

```

### 2. Where to Put Your Games (ROMs)

For the default configured games, make sure to rename your legally obtained files as follows:

* **Super Mario Galaxy 1:** `games/marioGalaxy/SuperMarioGalaxy.wbfs`
* **Super Mario Galaxy 2:** `games/marioGalaxy2/SuperMarioGalaxy2.wbfs`
* **Super Mario Sunshine:** `games/mariosunshine/SuperMarioSunshine.iso`
* **Mario 3D Land (3DS):** `games/mario3dland/sm3dland.cci` (decrypted version) - rename from .3ds to .cci, it's that simple.
* **Mario 64 DS:** `games/mario64DS/Mario64DS.nds`

> **Note:** If your files have different names, you must edit the corresponding `run` file with a text editor and change the filename at the end of the line.

---

## ➕ How to Add a New Game (Editing `games.json`)

If you want to expand your collection, you need to edit the `games.json` file in the program's root directory. Each game is a block between curly braces `{ }`.

**Steps to add a new one:**

1. **Create the folder:** Create `games/my_new_game/`.
2. **Create the script:** Copy a `run` file from another game and edit it to point to your new binary or ROM.
3. **Register in JSON:** Add an entry like this at the end of the `games.json` file:

```json
{
  "nombre": "Game Name",
  "tipo": "binario",
  "ruta_ejecutable": "games/my_new_game/run",
  "icon": "assets/my_new_game/icon.png",
  "logo": "assets/my_new_game/logo.png",
  "sound": "assets/my_new_game/sound.wav"
}

```

### Art Requirements:

* **Icon:** Game image (recommended icon.png: PNG image data, 1920 x 1920, PNG with transparency).
* **Logo:** Game title (logo.png: PNG image data, 552 x 322, transparent PNG).
* **Sound:** A short `.wav` file that will play when selecting the game.

---

## 🎮 Quick Controls

* **Arrow Keys / Left Stick:** Navigate between games.
* **Enter / A Button:** Launch game.
* **W-S / Right Stick:** Change background music.
* **Hold B Button (5 sec):** Safely close the Launcher.

---

### Gamepad and Emulator Configuration

> **⚠️ Important Note About Controls:**
> Every user has different gamepads. By default, the emulators come pre-configured, but if you need to remap your buttons or adjust the resolution, you must do it manually before starting the Launcher:
> 1. **For Dolphin (GameCube/Wii):**
> Go into the `dolphin-emulator/` folder and run the binary `./dolphin-emu`. There you can configure your gamepads in the "Controllers" menu and it will be saved permanently.
> 2. **For other emulators:**
> Access the corresponding folders (`3ds/`, `nds/`) and run the emulators directly to make your interface and control adjustments.
> 
> 
> Once configured to your liking, close the emulator and open the **3D All Stars Launcher** to enjoy the complete experience!

---

## Installation

> [!IMPORTANT]
> This repository uses Git LFS. Standard clones will not include the working binaries. **If you simply clone the repo without LFS, the emulator will fail to launch with "version not found" errors.**

1. **Install Git LFS on your system:**
* **Ubuntu/Debian:** `sudo apt install git-lfs`
* **Arch:** `sudo pacman -S git-lfs`
* **Fedora:** `sudo dnf install git-lfs`


2. **Clone and Setup:**

```bash
# 1. Clone the repository
git clone --depth=1 https://github.com/retired64/3D-All-Stars-Linux-EDITION.git

cd 3D-All-Stars-Linux-EDITION

# 2. Initialize LFS and pull the actual binaries
git lfs install
git lfs pull

# 3. Grant execution permissions to emulators and run scripts
chmod +x dolphin-emulator/dolphin-emu 3ds/azahar.AppImage nds/melonDS games/*/run
# 4. Set up Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt 

# 6. Launch!
python3 main.py 

```

<div align="center">

**Enjoyed this project? Consider giving it a ⭐**

</div>

### Project Status

This is a pre-release version.
Expect:

* Possible bugs
* Missing features
* Limited distro testing

Community feedback is highly appreciated.

## 🛠 Troubleshooting

### Emulator does not launch
- Make sure Git LFS pulled the binaries
- Check execute permissions (`chmod +x`)
- Run the `run` file manually to see errors

## System Requirements

### Minimum Specifications (Dolphin Emulator)

To run **GameCube and Wii** games through Dolphin Emulator, your system must meet:

| Component | Minimum Specification | Recommended |
|-----------|----------------------|-------------|
| **CPU** | Dual-core processor with high IPC<br>(Intel Core i3-6100 / AMD Ryzen 3 1200) | Quad-core at 3.5+ GHz with high IPC<br>(Intel Core i5-8400 / AMD Ryzen 5 3600 or newer) |
| **GPU** | DirectX 11.1 or OpenGL 4.4 compatible<br>Intel HD 4000 / AMD Radeon HD 5000 / NVIDIA GT 730 | Mid-range or better GPU<br>NVIDIA GTX 1050 / AMD RX 560 or higher |
| **RAM** | 2 GB | 4 GB or more |
| **Operating System** | Ubuntu 20.04+ / Debian 10+ (64-bit)<br>(Kernel 5.4+) | Ubuntu 22.04+ / Debian 11+ (64-bit) |
| **Disk Space** | 5 GB (excluding ROMs) | 10 GB+ (with multiple games) |
| **Dependencies** | `libevdev`, `libusb`, `pulseaudio` | Proprietary GPU driver recommended |

### Important Notes

> **⚠️ CPU Performance:** Dolphin is a **dual-core application** that relies heavily on **IPC (Instructions Per Clock)** and **clockspeed**. Additional cores beyond four won't significantly improve performance. Dolphin uses two cores for main emulation, a third for other tasks, and a fourth for the OS and background processes.

> **🎮 GPU Requirements:** Your GPU **must support DirectX 11.1 or OpenGL 4.4** to run Dolphin efficiently. Older GPUs (10+ years) or low-end models may struggle and are not recommended. Dolphin uses modern graphics APIs to reduce overhead.

> **Driver Recommendations:**
> - **NVIDIA:** Any modern mid-range or better GPU works well with Ubershaders
> - **AMD:** Performs best with DirectX over OpenGL. Use D3D backend for optimal performance
> - **Intel:** Iris Pro iGPUs work with D3D on Windows, but a discrete GPU is highly recommended

> **RAM:** 2 GB minimum is required. RAM speed and quantity generally do not affect emulation speed significantly.

> **Performance Varies by Game:** Some games use easy-to-emulate features and run full-speed on modest hardware, while others struggle even on powerful processors. Performance depends heavily on what the game instructs the emulator to do.

### Additional Emulators Included

- **Azahar/Citra (3DS):** Similar requirements to Dolphin but generally lighter. Dual-core CPU at 2.5+ GHz recommended.
- **DeSmuME (DS):** Very lightweight, runs on almost any modern system with minimal resources.

---

### Verify Compatibility

Before installing, check your hardware meets the requirements:

```bash
# Check CPU information and cores
lscpu | grep -E "Model name|CPU\(s\)"

# Check GPU and OpenGL support (requires mesa-utils)
glxinfo | grep "OpenGL version"

# Check available RAM
free -h

# Verify 64-bit OS
uname -m   # Should return "x86_64"
```

> **⚠️ 32-bit Systems Not Supported:** Dolphin requires a 64-bit operating system. The emulator will not run on 32-bit Linux distributions.

### Performance Tips

- **Use proprietary GPU drivers** (NVIDIA/AMD) instead of open-source alternatives for best performance
- **Enable Ubershaders** in Dolphin settings to reduce stuttering
- If experiencing lag, **reduce internal resolution** to 1x (native GameCube/Wii resolution)
- Ensure **no background tasks** are consuming CPU resources during gameplay
- For specific game performance questions, check the [Dolphin Wiki](dolphin-emu.org/docs/faq/#what-operating-systems-are-supported) compatibility database

## 🔗 Useful Links

* [Report a Bug](https://github.com/retired64/3D-All-Stars-Linux-EDITION/issues/new?labels=bug)
* [Request a Feature](https://github.com/retired64/3D-All-Stars-Linux-EDITION/issues/new?labels=enhancement)
* [Join Discussions](https://github.com/retired64/3D-All-Stars-Linux-EDITION/discussions)

## ⚠️ Legal Disclaimer

> [!CAUTION]
> This project does not include any ROMs or copyrighted game files. Users are responsible for providing legally obtained backups.

<div align="center">
<img src="src/img/retired64.png" alt="Retired64" width="400"/>

  *Developed with ❤️ by **Retired64***
[https://www.youtube.com/@Retired64](https://www.youtube.com/@Retired64)

</div>

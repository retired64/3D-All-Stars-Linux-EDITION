![Banner 3D All Stars Linux EDITION](src/img/logo.png)

<div align="center">
  
  <a href="https://github.com/retired64/3D-All-Stars-Linux-EDITION/fork">
    <img src="src/img/fork.png" alt="Fork this repository" width="140" />
  </a>
    
  ![GitHub forks](https://img.shields.io/github/forks/retired64/3D-All-Stars-Linux-EDITION?style=social)
  ![GitHub stars](https://img.shields.io/github/stars/retired64/3D-All-Stars-Linux-EDITION?style=social)
  
</div>

**Version:** 1.0 (Pre-release)
**Platform:** Linux
**Release Page:** [3D All Stars Linux EDITION Pre-release](https://github.com/retired64/3D-All-Stars-Linux-EDITION/releases)

# User Guide: 3D All Stars Deluxe Launcher (Linux)

Welcome to 3D All Stars Linux EDITION! This program is designed to give you a console-like "Plug & Play" experience with gamepad support, ambient music, and a smooth interface.

<div align="center">
  <img src="src/img/potential.png" alt="Potential" width="400"/>
</div>

This isn't just a game menu; it's a **unified command center**.

* **Full Compatibility:** Thanks to the `run` file system, you can launch virtually anything: Emulators (Dolphin, Citra, Desmume), native Linux games, or even custom scripts.
* **Immersive Experience:** Includes background video loading, individual sound effects per game, and optimized navigation.
* **Portability:** If you maintain the folder structure, you can take your collection to any PC with Ubuntu/Debian or other Linux distributions (not yet tested on all distros).

---

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
* **Super Mario Sunshine:** `games/marioshunshine/SuperMarioSunshine.iso`
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
>    Go into the `dolphin-emulator/` folder and run the binary `./dolphin-emu`. There you can configure your gamepads in the "Controllers" menu and it will be saved permanently.
> 2. **For other emulators:**
>    Access the corresponding folders (`3ds/`, `nds/`) and run the emulators directly to make your interface and control adjustments.
> 
> 
> Once configured to your liking, close the emulator and open the **3D All Stars Launcher** to enjoy the complete experience!

---

<div align="center">
  <img src="src/img/retired64.png" alt="Retired64" width="400"/>
</div>

_Developed with ❤️ by **Retired64**_
[https://www.youtube.com/@Retired64](https://www.youtube.com/@Retired64)

![Banner 3D All Stars Linux EDITION](src/img/logo.png)

# Guía de Usuario: 3D All Stars Deluxe Launcher (Linux)

¡Bienvenido a 3D All Stars Linux EDITION! Este programa ha sido diseñado para ofrecerte una experiencia de consola "Plug & Play", con soporte para mando, música ambiental y una interfaz fluida.

## El Potencial del Launcher

Este no es solo un menú de juegos; es un **centro de mando unificado**.

* **Compatibilidad Total:** Gracias al sistema de archivos `run`, puedes lanzar prácticamente cualquier cosa: Emuladores (Dolphin, Citra, Desmume), juegos nativos de Linux o incluso scripts personalizados.
* **Experiencia Inmersiva:** Incluye carga de video de fondo, sonidos individuales por juego y navegación optimizada.
* **Portabilidad:** Si mantienes la estructura de carpetas, puedes llevar tu colección a cualquier PC con Ubuntu/Debian o otras Distribuciones LInux Aun no probado.

---

## Cómo configurar tus propios juegos

Para que el Launcher funcione, debes colocar tus archivos siguiendo la estructura que el programa espera.

### 1. La importancia del archivo `run`

Cada juego dentro de la carpeta `games/nombre_del_juego/` tiene un archivo llamado `run`.
**¿Para qué sirve?** Es un "puente". En lugar de que el Launcher intente adivinar cómo abrir cada emulador, el Launcher simplemente ejecuta `run`, y este script se encarga de abrir el emulador con la configuración y la ROM correcta.

**Ejemplo de cómo debe verse un archivo `run` (para Dolphin/GameCube):**

```bash
#!/bin/sh
cd "$(dirname "$0")" || exit 1
# Llama al emulador y carga la ISO que pongas en esa carpeta
../../dolphin-emulator/dolphin-emu -b -e MiJuego.iso

```

### 2. Dónde poner tus juegos (Roms)

Para los juegos configurados por defecto, asegúrate de renombrar tus archivos legalmente obtenidos de la siguiente manera:

* **Super Mario Galaxy 1:** `games/marioGalaxy/SuperMarioGalaxy.wbfs`
* **Super Mario Galaxy 2:** `games/marioGalaxy2/SuperMarioGalaxy2.wbfs`
* **Super Mario Sunshine:** `games/marioshunshine/SuperMarioSunshine.iso`
* **Mario 3D Land (3DS):** `games/mario3dland/sm3dland.cci` (version desencriptada) la renombras de .3ds a .cci asi de facil.
* **Mario 64 DS:** `games/mario64DS/Mario64DS.nds`

> **Nota:** Si tus archivos tienen nombres diferentes, debes editar el archivo `run` correspondiente con un editor de texto y cambiar el nombre del archivo al final de la línea.

---

## ➕ Cómo agregar un juego nuevo (Modificando `games.json`)

Si quieres expandir tu colección, debes editar el archivo `games.json` en la raíz del programa. Cada juego es un bloque entre llaves `{ }`.

**Pasos para agregar uno nuevo:**

1. **Crea la carpeta:** Crea `games/mi_nuevo_juego/`.
2. **Crea el script:** Copia un archivo `run` de otro juego y edítalo para que apunte a tu nuevo binario o ROM.
3. **Registra en el JSON:** Añade una entrada como esta al final del archivo `games.json`:

```json
{
  "nombre": "Nombre del juego",
  "tipo": "binario",
  "ruta_ejecutable": "games/mi_nuevo_juego/run",
  "icon": "assets/mi_nuevo_juego/icon.png",
  "logo": "assets/mi_nuevo_juego/logo.png",
  "sound": "assets/mi_nuevo_juego/sonido.wav"
}

```

### Requisitos de Arte:

* **Icon:** Imagen del juego (se recomienda icon.png: PNG image data, 1920 x 1920, PNG con transparencia).
* **Logo:** Título del juego (logo.png: PNG image data, 552 x 322, PNG transparente).
* **Sound:** Un archivo `.wav` corto que sonará al seleccionar el juego.

---

## 🎮 Controles Rápidos

* **Flechas / Stick Izquierdo:** Navegar entre juegos.
* **Enter / Botón A:** Lanzar juego.
* **W-S / Stick Derecho:** Cambiar música de fondo.
* **Mantener Botón B (5 seg):** Cerrar el Launcher de forma segura.

---


### Configuración de Mandos y Emuladores

> **⚠️ Nota Importante sobre los Controles:**
> Cada usuario tiene mandos diferentes. Por defecto, los emuladores vienen pre-configurados, pero si necesitas remapear tus botones o ajustar la resolución, debes hacerlo manualmente antes de iniciar el Launcher:
> 1. **Para Dolphin (GameCube/Wii):** >    Entra en la carpeta `dolphin-emulator/` y ejecuta el binario `./dolphin-emu`. Allí podrás configurar tus mandos en el menú de "Mandos" y se guardarán para siempre.
> 2. **Para otros emuladores:** >  Accede a las carpetas correspondientes (`3ds/`, `nds/`) y ejecuta los emuladores directamente para realizar tus ajustes de interfaz y control.
> 
> 
> Una vez configurados a tu gusto, ¡cierra el emulador y abre el **3D All Stars Launcher** para disfrutar de la experiencia completa!


_Desarrollado con ❤️ por **Retired64**_ 
[https://www.youtube.com/@Retired64](https://www.youtube.com/@Retired64)

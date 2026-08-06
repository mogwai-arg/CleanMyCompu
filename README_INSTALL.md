# CleanMyCompu — Guía de build + distribución (Windows)

## Para VOS (dev) — 2 pasos

### 1. Compilar el .exe
Doble clic en **`build_win.bat`**.

Se abre una ventana bonita con barra de progreso. Tarda 3-8 minutos la primera vez (baja PySide6, psutil, PyInstaller). Después es ~1-2 min por rebuild.

Al terminar: **`dist\CleanMyCompu\CleanMyCompu.exe`**.
Este .exe funciona solo pero es una carpeta grande (~200 MB). No sirve para mandar directamente.

### 2. Armar el instalador
**Una sola vez**: instalá Inno Setup gratis de <https://jrsoftware.org/isdl.php> (siguiente, siguiente, instalar).

Después: doble clic en **`build_installer.bat`**.

Se abre otra ventana con progreso. Tarda ~30 segundos. Al terminar tenés:

**`installer_output\CleanMyCompu-Setup-v1.4.0.exe`** — **UN SOLO ARCHIVO** de ~80 MB.

Este es el que le mandás a tu pareja.

---

## Para TU PAREJA — 3 pasos

1. **Recibir**: el archivo `CleanMyCompu-Setup-v1.4.0.exe` (mandale por WeTransfer, Google Drive, pendrive, WhatsApp, lo que sea).

2. **Instalar**: doble clic al .exe.
   - Puede aparecer una alerta azul de Windows Defender: **"Windows protegió tu equipo"**.
     Esto pasa porque el instalador no está firmado con certificado (los certificados cuestan ~$100/año).
     Solución: clic en **"Más información"** → botón **"Ejecutar de todos modos"**.
   - Aparece un wizard estándar de Windows:
     - **Siguiente** → aceptar ubicación (Program Files)
     - Marcar/desmarcar "Crear acceso directo en el escritorio"
     - **Instalar** → **Finalizar**

3. **Usar**: el ícono aparece en el escritorio y en el menú Inicio. Doble clic y listo.

**Para desinstalar**: Panel de Control → Programas → CleanMyCompu → Desinstalar. Se borra todo, incluyendo la config.

---

## Publicar una nueva versión

1. Editá `updater.py`: cambiar `__version__ = "1.4.0"` al nuevo número.
2. Editá `installer.iss`: cambiar `#define AppVersion "1.4.0"` al mismo número.
3. Corré `build_win.bat` → `build_installer.bat`.
4. Subí el instalador nuevo a GitHub Releases (o a donde estés distribuyendo).

---

## Problemas comunes

**"Failed to import encodings module"** al abrir el .exe:
- Corré `build_win.bat` de nuevo. A veces necesita 2 intentos.

**Inno Setup no aparece al correr `build_installer.bat`**:
- Verificá que lo instalaste con la opción por defecto. Debe estar en:
  `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`

**Windows Defender bloquea el .exe al bajarlo**:
- Es normal para .exes sin firma. La solución es "Más información → Ejecutar de todos modos".
- A largo plazo: firmar el binario con un cert de code signing (~$100/año en SSL.com o similar).

# Cómo publicar una nueva versión de CleanMyCompu

Este documento explica el proceso paso a paso para que, cuando saques una nueva
versión, **todos los usuarios que tengan la app instalada reciban la
notificación** al abrirla y puedan descargar la nueva.

---

## Cómo funciona el sistema de updates

Cuando alguien abre CleanMyCompu, 2 segundos después la app hace una petición
silenciosa a una URL con un archivo JSON llamado `latest.json`. Ese JSON tiene:

```json
{
  "version": "1.2.0",
  "url": "https://github.com/USUARIO/CleanMyCompu/releases/download/v1.2.0/CleanMyCompu.dmg",
  "notes": "- Agregado X\n- Fixed Y"
}
```

La app compara `version` con la versión que tiene instalada (`__version__`
en `updater.py`). Si el JSON tiene una mayor, muestra:

1. **Notificación nativa de macOS** — "CleanMyCompu 1.2.0 disponible"
2. **Indicador clickeable en el sidebar** — "⬇ v1.2.0 disponible — clic para descargar"

El click abre la URL del JSON en el navegador default del usuario.

---

## Setup una única vez: hospedar el `latest.json`

Cualquier lugar donde puedas subir un archivo público sirve. La recomendación
es **GitHub Releases** porque es gratis, versionado y confiable.

### Opción A — GitHub (recomendada)

1. **Crear el repo** (solo una vez):
   - Andá a https://github.com/new
   - Nombre: `CleanMyCompu`
   - Público o privado — si es privado, la URL raw no sirve. **Ponelo público.**
   - Sin README, sin gitignore. Crear.

2. **Anotate tu usuario/repo**, por ejemplo `mi-usuario/CleanMyCompu`.

3. **Editar `updater.py`** una única vez:
   ```python
   MANIFEST_URL = (
       "https://raw.githubusercontent.com/mi-usuario/CleanMyCompu/"
       "main/latest.json"
   )
   ```
   Reemplazá `mi-usuario` por el tuyo.

4. **Crear el archivo `latest.json`** en la raíz del repo con el contenido de
   tu versión actual. La primera vez subís `1.1.0` (la que estás publicando ahora):
   ```json
   {
     "version": "1.1.0",
     "url": "https://github.com/mi-usuario/CleanMyCompu/releases/download/v1.1.0/CleanMyCompu.dmg",
     "notes": "Primera release pública"
   }
   ```

5. **Subir el `.dmg`** a **Releases**:
   - En tu repo → *Releases* → *Create a new release*
   - Tag: `v1.1.0`
   - Título: `CleanMyCompu v1.1.0`
   - Attachments: arrastrá tu `dist/CleanMyCompu.dmg`
   - *Publish release*

**Listo el setup.** Rebuildeá la app (`./build_app.sh` + `./share_app.sh`),
distribuí este `.dmg` a tus amigos. Todos van a tener la URL configurada.

### Opción B — Gist (más rápido, sin repo)

1. Andá a https://gist.github.com
2. Filename: `latest.json`
3. Contenido: el JSON de arriba
4. Public gist → *Create*
5. Click en `Raw` — copiá la URL
6. Ponela en `MANIFEST_URL` de `updater.py`

Contra: no tenés "Releases" para hostear los `.dmg`. Tenés que subirlos aparte
(Google Drive, WeTransfer, S3, tu propia web).

---

## Cada nueva versión — checklist

Cada vez que quieras sacar una nueva versión (ej. v1.1.0 → v1.2.0):

### 1. Levantar la versión en el código

**Archivo `updater.py`:**
```python
__version__ = "1.2.0"   # ← bumpéalo
```

Reglas semver simples:
- **Patch** (`1.1.0 → 1.1.1`): bugfixes chicos
- **Minor** (`1.1.0 → 1.2.0`): features nuevas sin romper nada
- **Major** (`1.1.0 → 2.0.0`): cambios grandes o incompatibles

### 2. Rebuildear la `.app` y el `.dmg`

```bash
cd /Users/Javi/Documents/claude/limpiador
./build_app.sh
./share_app.sh
```

Tenés `dist/CleanMyCompu.app` y `dist/CleanMyCompu.dmg` frescos.

### 3. Subir el `.dmg` a GitHub Releases

- Repo → *Releases* → *Draft a new release*
- Tag: `v1.2.0` (con la v adelante)
- Título: `CleanMyCompu v1.2.0`
- Notes: pegá los cambios (van a aparecer también en la notificación)
- Attach `dist/CleanMyCompu.dmg`
- *Publish release*

Anotate la URL del `.dmg` — algo tipo:
`https://github.com/mi-usuario/CleanMyCompu/releases/download/v1.2.0/CleanMyCompu.dmg`

### 4. Actualizar `latest.json` en el repo

Editá el archivo desde la web de GitHub (o clonando local):

```json
{
  "version": "1.2.0",
  "url": "https://github.com/mi-usuario/CleanMyCompu/releases/download/v1.2.0/CleanMyCompu.dmg",
  "notes": "- Feature nueva X\n- Fix del bug Y\n- Mejoré Z"
}
```

Commit + push. **Este es el paso que dispara la notificación** a todos los
usuarios existentes.

### 5. Probar que la notificación funciona

Antes de "publicar de verdad" (avisarle a tu amigo), verificá que la
notificación llega correctamente:

1. En **otra** Mac (o abrí `dist/CleanMyCompu.app` desde tu misma Mac
   siempre y cuando la que tenías tenga una `__version__` menor a la nueva).
2. Esperá 2-5 segundos.
3. Debería aparecer la notif nativa de macOS.
4. Debería aparecer el indicador clickeable en el sidebar footer.
5. Click en el indicador → se abre el `.dmg` en el navegador.

Si NO aparece:
- Chequeá que el JSON en la URL de `MANIFEST_URL` esté bien formateado
  (podés abrirlo desde el navegador — tiene que devolver el JSON en crudo)
- Chequeá que `version` en el JSON sea mayor a la instalada
- Chequeá que las notificaciones de terminal-notifier estén habilitadas
  en *Preferencias del Sistema → Notificaciones*

---

## Notas importantes

**La URL del manifest se lee del `.app` viejo.** Los usuarios que instalaron
v1.0.0 y v1.1.0 van a consultar la URL que estaba en `updater.py` en el
momento del build. **Nunca cambies la URL** una vez que empezaste a
distribuir — usá siempre la misma, y solo cambiá el contenido del JSON.

**Los usuarios tienen que abrir la app** para ver la notif — no hay
polling en background si la app está cerrada. Esto es intencional: si
abrieron la app, están usándola, es el momento perfecto para avisar.

**Un usuario que no quiere update** simplemente ignora la notificación
y sigue usando su versión. No hay auto-update forzado.

**Cambios de la URL en `updater.py` sin rebuildear NO afectan** a los
usuarios ya instalados. Solo afectan al próximo `.dmg` que buildees y
distribuyas. Por eso: fijá la URL bien la primera vez.

---

## Resumen de comandos

```bash
# Setup inicial (una vez): editar updater.py con MANIFEST_URL real,
#                          crear repo GitHub, primera release

# Cada release:
vi updater.py               # bumpear __version__
./build_app.sh              # regenera dist/CleanMyCompu.app
./share_app.sh              # regenera dist/CleanMyCompu.dmg

# Subir a GitHub Releases (via web) + editar latest.json en el repo.

# Listo. Los usuarios reciben la notif al abrir la app.
```

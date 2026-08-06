# CleanMyCompu - build .exe con UI de progreso (Windows Forms).
# Todo en ASCII para evitar problemas de encoding con Windows PowerShell 5.1.
# Uso:  powershell -ExecutionPolicy Bypass -File build_win.ps1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Set-Location $PSScriptRoot

$form = New-Object System.Windows.Forms.Form
$form.Text = "CleanMyCompu - Compilando"
$form.Size = New-Object System.Drawing.Size(680, 460)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $true
$form.BackColor = [System.Drawing.Color]::White
$form.Font = New-Object System.Drawing.Font("Segoe UI", 9)

$title = New-Object System.Windows.Forms.Label
$title.Text = "Compilando CleanMyCompu.exe"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(29, 29, 31)
$title.Location = New-Object System.Drawing.Point(24, 20)
$title.Size = New-Object System.Drawing.Size(640, 32)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "Esto tarda entre 3 y 8 minutos la primera vez. Andate a tomar un cafe."
$subtitle.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(110, 110, 115)
$subtitle.Location = New-Object System.Drawing.Point(24, 56)
$subtitle.Size = New-Object System.Drawing.Size(640, 20)
$form.Controls.Add($subtitle)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Preparando..."
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$statusLabel.ForeColor = [System.Drawing.Color]::FromArgb(29, 29, 31)
$statusLabel.Location = New-Object System.Drawing.Point(24, 92)
$statusLabel.Size = New-Object System.Drawing.Size(640, 24)
$form.Controls.Add($statusLabel)

$progress = New-Object System.Windows.Forms.ProgressBar
$progress.Location = New-Object System.Drawing.Point(24, 122)
$progress.Size = New-Object System.Drawing.Size(632, 22)
$progress.Style = "Continuous"
$progress.Minimum = 0
$progress.Maximum = 100
$progress.Value = 0
$form.Controls.Add($progress)

$logLabel = New-Object System.Windows.Forms.Label
$logLabel.Text = "Detalle:"
$logLabel.Font = New-Object System.Drawing.Font("Segoe UI", 9)
$logLabel.ForeColor = [System.Drawing.Color]::FromArgb(110, 110, 115)
$logLabel.Location = New-Object System.Drawing.Point(24, 158)
$logLabel.Size = New-Object System.Drawing.Size(200, 20)
$form.Controls.Add($logLabel)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Multiline = $true
$logBox.ScrollBars = "Vertical"
$logBox.ReadOnly = $true
$logBox.Location = New-Object System.Drawing.Point(24, 182)
$logBox.Size = New-Object System.Drawing.Size(632, 180)
$logBox.Font = New-Object System.Drawing.Font("Consolas", 8)
$logBox.BackColor = [System.Drawing.Color]::FromArgb(245, 245, 247)
$logBox.WordWrap = $false
$form.Controls.Add($logBox)

$openBtn = New-Object System.Windows.Forms.Button
$openBtn.Text = "Abrir carpeta dist"
$openBtn.Location = New-Object System.Drawing.Point(370, 380)
$openBtn.Size = New-Object System.Drawing.Size(160, 32)
$openBtn.FlatStyle = "Flat"
$openBtn.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(200, 200, 205)
$openBtn.BackColor = [System.Drawing.Color]::White
$openBtn.Enabled = $false
$openBtn.Add_Click({
    Start-Process explorer.exe -ArgumentList "$PSScriptRoot\dist\CleanMyCompu"
})
$form.Controls.Add($openBtn)

$closeBtn = New-Object System.Windows.Forms.Button
$closeBtn.Text = "Cerrar"
$closeBtn.Location = New-Object System.Drawing.Point(540, 380)
$closeBtn.Size = New-Object System.Drawing.Size(116, 32)
$closeBtn.FlatStyle = "Flat"
$closeBtn.BackColor = [System.Drawing.Color]::FromArgb(52, 199, 89)
$closeBtn.ForeColor = [System.Drawing.Color]::White
$closeBtn.FlatAppearance.BorderSize = 0
$closeBtn.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$closeBtn.Enabled = $false
$closeBtn.Add_Click({ $form.Close() })
$form.Controls.Add($closeBtn)

function Set-Progress {
    param([int]$percent, [string]$status)
    $script:progress.Value = [Math]::Min(100, [Math]::Max(0, $percent))
    if ($status) { $script:statusLabel.Text = $status }
    [System.Windows.Forms.Application]::DoEvents()
}

function Add-Log {
    param([string]$text)
    if (-not $text) { return }
    $ts = Get-Date -Format "HH:mm:ss"
    $script:logBox.AppendText("[$ts] $text`r`n")
    $script:logBox.SelectionStart = $script:logBox.Text.Length
    $script:logBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

function Invoke-Silent {
    # OJO: no usar $args como nombre de parametro, es variable reservada de PowerShell.
    param([string]$exe, [string[]]$argList, [string]$phase, [bool]$marquee=$false)
    Add-Log "> $phase"

    # Convertir path relativo a absoluto
    if (-not [System.IO.Path]::IsPathRooted($exe)) {
        $absExe = Join-Path $PSScriptRoot $exe
        if (Test-Path $absExe) {
            $exe = $absExe
        }
    }
    if (-not (Test-Path $exe)) {
        Add-Log "! ERROR: no existe el ejecutable: $exe"
        return 998
    }
    Add-Log "  exe: $exe"
    Add-Log "  args: $($argList -join ' ')"

    if ($marquee) {
        $script:progress.Style = "Marquee"
        $script:progress.MarqueeAnimationSpeed = 30
    }

    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName()

    try {
        # Uso .NET Process directo para tener control total sobre ExitCode.
        # (Start-Process -PassThru tiene bugs conocidos con ExitCode.)
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $exe
        # Buildear Arguments string con quoting adecuado
        $quoted = @()
        foreach ($a in $argList) {
            if ($a -match '\s' -and $a -notmatch '^".*"$') {
                $quoted += '"' + $a + '"'
            } else {
                $quoted += $a
            }
        }
        $psi.Arguments = $quoted -join " "
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.WorkingDirectory = $PSScriptRoot

        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $psi

        # Buffers para output async (evita deadlock)
        $script:outBuf = New-Object System.Text.StringBuilder
        $script:errBuf = New-Object System.Text.StringBuilder

        $outAction = {
            if (-not [string]::IsNullOrEmpty($EventArgs.Data)) {
                [void]$Event.MessageData.AppendLine($EventArgs.Data)
            }
        }

        $subOut = Register-ObjectEvent -InputObject $p -EventName OutputDataReceived `
            -MessageData $script:outBuf -Action $outAction
        $subErr = Register-ObjectEvent -InputObject $p -EventName ErrorDataReceived `
            -MessageData $script:errBuf -Action $outAction

        $started = $p.Start()
        if (-not $started) {
            Add-Log "! No se pudo iniciar el proceso"
            Unregister-Event -SourceIdentifier $subOut.Name
            Unregister-Event -SourceIdentifier $subErr.Name
            if ($marquee) { $script:progress.Style = "Continuous" }
            return 997
        }
        $p.BeginOutputReadLine()
        $p.BeginErrorReadLine()
    } catch {
        Add-Log "! Excepcion lanzando proceso: $($_.Exception.Message)"
        Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue
        if ($marquee) { $script:progress.Style = "Continuous" }
        return 999
    }

    # Polling loop — mantiene UI viva y va escribiendo output al log
    $lastOutLen = 0
    $lastErrLen = 0
    while (-not $p.HasExited) {
        $outText = $script:outBuf.ToString()
        if ($outText.Length -gt $lastOutLen) {
            $newContent = $outText.Substring($lastOutLen)
            foreach ($l in $newContent -split "`r?`n") {
                if ($l.Trim()) { Add-Log $l.TrimEnd() }
            }
            $lastOutLen = $outText.Length
        }
        $errText = $script:errBuf.ToString()
        if ($errText.Length -gt $lastErrLen) {
            $newContent = $errText.Substring($lastErrLen)
            foreach ($l in $newContent -split "`r?`n") {
                if ($l.Trim()) { Add-Log ("! " + $l.TrimEnd()) }
            }
            $lastErrLen = $errText.Length
        }
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 150
    }

    # CRITICO: forzar sincronizacion final para poblar ExitCode correctamente
    $p.WaitForExit()

    # Drenar cualquier output que quedo en los buffers
    Start-Sleep -Milliseconds 300
    [System.Windows.Forms.Application]::DoEvents()
    $outText = $script:outBuf.ToString()
    if ($outText.Length -gt $lastOutLen) {
        foreach ($l in $outText.Substring($lastOutLen) -split "`r?`n") {
            if ($l.Trim()) { Add-Log $l.TrimEnd() }
        }
    }
    $errText = $script:errBuf.ToString()
    if ($errText.Length -gt $lastErrLen) {
        foreach ($l in $errText.Substring($lastErrLen) -split "`r?`n") {
            if ($l.Trim()) { Add-Log ("! " + $l.TrimEnd()) }
        }
    }

    # Cleanup event subscribers
    try {
        Unregister-Event -SourceIdentifier $subOut.Name -ErrorAction SilentlyContinue
        Unregister-Event -SourceIdentifier $subErr.Name -ErrorAction SilentlyContinue
    } catch { }

    Remove-Item $outFile, $errFile -Force -ErrorAction SilentlyContinue

    if ($marquee) {
        $script:progress.Style = "Continuous"
    }

    $rc = $p.ExitCode
    Add-Log "  exit code: $rc"
    return $rc
}

function Run-Build {
    try {
        Set-Progress 5 "Chequeando entorno virtual..."
        if (-not (Test-Path ".venv")) {
            Add-Log "Creando entorno virtual (.venv)..."
            $rc = Invoke-Silent "python" @("-m", "venv", ".venv") "python -m venv .venv"
            if ($rc -ne 0) {
                Add-Log "ERROR: no se encontro Python. Instalalo desde https://www.python.org/downloads/"
                Set-Progress 100 "Fallo: falta Python"
                return $false
            }
        }
        Set-Progress 15 "Entorno virtual OK."

        # Verificar que pip.exe existe realmente
        $pipExe = Join-Path $PSScriptRoot ".venv\Scripts\pip.exe"
        if (-not (Test-Path $pipExe)) {
            Add-Log "ERROR: no existe $pipExe"
            Add-Log "El entorno virtual esta corrupto. Borra la carpeta .venv y corre de nuevo."
            Set-Progress 100 "Fallo: .venv corrupto (borra la carpeta .venv y reinicia)"
            return $false
        }
        Add-Log "OK: pip.exe existe en $pipExe"

        Set-Progress 20 "Actualizando pip..."
        # SIN --quiet para ver output real
        Invoke-Silent ".venv\Scripts\python.exe" @("-m", "pip", "install", "--upgrade", "pip") "pip upgrade" | Out-Null

        Set-Progress 30 "Instalando dependencias (PySide6, psutil, pyinstaller, send2trash)..."
        Add-Log "Esto puede tardar 2-5 minutos bajando ~50 MB. Aguantame..."
        # SIN --quiet + usando python -m pip por si pip.exe tiene problemas
        $rc = Invoke-Silent ".venv\Scripts\python.exe" @("-m", "pip", "install", "PySide6", "send2trash", "psutil", "pyinstaller") "pip install deps" $true
        if ($rc -ne 0) {
            Add-Log "ERROR: pip install fallo con exit code $rc."
            Add-Log "Mira las lineas de arriba: si aparece 'Could not find' es problema de red/version."
            Add-Log "Si aparece 'permission denied', corre el .bat como administrador."
            Add-Log "Si nada aparece, probablemente el .venv esta roto: borra la carpeta .venv y probar de nuevo."
            Set-Progress 100 "Fallo: pip install (ver detalle arriba)"
            return $false
        }
        Set-Progress 45 "Dependencias listas."

        Set-Progress 48 "Generando icono..."
        if (-not (Test-Path "assets\AppIcon.ico")) {
            $iconCode = "from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); from icons import make_logo_pixmap; pm = make_logo_pixmap(size=256, bg='#1D1D1F', fg='#FFFFFF', radius_ratio=0.225, padding_ratio=0.09); pm.setDevicePixelRatio(1.0); pm.save('assets/AppIcon.ico', 'ICO')"
            Invoke-Silent ".venv\Scripts\python.exe" @("-c", "`"$iconCode`"") "generar icono" | Out-Null
        }

        Set-Progress 55 "Compilando .exe con PyInstaller (2 a 5 minutos)..."
        $pyi = @(
            "--windowed", "--name", "CleanMyCompu",
            "--icon", "assets\AppIcon.ico",
            "--add-data", "`"assets;assets`"",
            "--collect-all", "encodings",
            "--collect-submodules", "PySide6",
            "--collect-submodules", "psutil",
            "--hidden-import", "PySide6.QtSvg",
            "--hidden-import", "psutil._psutil_windows",
            "--clean", "--noconfirm",
            "main.py"
        )
        $rc = Invoke-Silent ".venv\Scripts\pyinstaller.exe" $pyi "PyInstaller build" $true
        if ($rc -ne 0) {
            Add-Log "ERROR: PyInstaller fallo."
            Set-Progress 100 "Fallo: mira el log arriba."
            return $false
        }

        Set-Progress 100 "Listo - dist\CleanMyCompu\CleanMyCompu.exe"
        Add-Log ""
        Add-Log "==============================================="
        Add-Log "BUILD OK. El .exe esta en: dist\CleanMyCompu\CleanMyCompu.exe"
        Add-Log "==============================================="
        Add-Log ""
        Add-Log "Para armar el instalador que le mandas a tu pareja:"
        Add-Log "  1. Instala Inno Setup: https://jrsoftware.org/isdl.php"
        Add-Log "  2. Corre build_installer.bat"
        Add-Log ""
        return $true
    } catch {
        Add-Log "EXCEPCION: $_"
        Set-Progress 100 "Fallo: excepcion inesperada"
        return $false
    }
}

$form.Add_Shown({
    $ok = Run-Build
    $closeBtn.Enabled = $true
    $openBtn.Enabled = $ok
    if ($ok) {
        $closeBtn.Text = "Cerrar"
    } else {
        $closeBtn.Text = "Cerrar (con errores)"
        $closeBtn.BackColor = [System.Drawing.Color]::FromArgb(255, 59, 48)
    }
})

[void]$form.ShowDialog()

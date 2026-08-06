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
    param([string]$exe, [string[]]$args, [string]$phase)
    Add-Log "> $phase"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.Arguments = ($args -join " ")
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $p = [System.Diagnostics.Process]::Start($psi)
    while (-not $p.HasExited) {
        while (-not $p.StandardOutput.EndOfStream) {
            $line = $p.StandardOutput.ReadLine()
            if ($line) { Add-Log $line }
        }
        [System.Windows.Forms.Application]::DoEvents()
        Start-Sleep -Milliseconds 40
    }
    $tail = $p.StandardOutput.ReadToEnd()
    if ($tail) { foreach ($l in $tail -split "`r?`n") { if ($l) { Add-Log $l } } }
    $err = $p.StandardError.ReadToEnd()
    if ($err) { foreach ($l in $err -split "`r?`n") { if ($l) { Add-Log "! $l" } } }
    return $p.ExitCode
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

        Set-Progress 20 "Actualizando pip..."
        Invoke-Silent ".venv\Scripts\pip.exe" @("install", "--quiet", "--upgrade", "pip") "pip upgrade" | Out-Null

        Set-Progress 30 "Instalando dependencias (PySide6, psutil, pyinstaller, send2trash)..."
        $rc = Invoke-Silent ".venv\Scripts\pip.exe" @("install", "--quiet", "PySide6", "send2trash", "psutil", "pyinstaller") "pip install deps"
        if ($rc -ne 0) {
            Add-Log "ERROR: fallo pip install."
            Set-Progress 100 "Fallo: no se pudieron instalar dependencias"
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
        $rc = Invoke-Silent ".venv\Scripts\pyinstaller.exe" $pyi "PyInstaller build"
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

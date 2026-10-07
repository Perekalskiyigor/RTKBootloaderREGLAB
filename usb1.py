# usb_power_cycle.py
import sys
import ctypes

# Права админа
if not ctypes.windll.shell32.IsUserAnAdmin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
    sys.exit()

import subprocess
import time

print("🔌 ПОЛНОЕ ОТКЛЮЧЕНИЕ ПИТАНИЯ USB ПОРТА")
print("=" * 40)

# Используем USBPcap для полного сброса (если установлен)
# Или devcon с принудительным удалением драйверов

ps_hard_reset = '''
# Самый жесткий метод - через реестр
Write-Host "Выполняю глубокий сброс USB..." -ForegroundColor Red

# 1. Удаляем из реестра все упоминания J-Link
$paths = @(
    "HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USB",
    "HKLM:\\SYSTEM\\CurrentControlSet\\Enum\\USBSTOR"
)

foreach ($path in $paths) {
    if (Test-Path $path) {
        Get-ChildItem $path -Recurse | Where-Object {
            $_.Name -like "*VID_1366*" -or $_.Name -like "*J-Link*"
        } | ForEach-Object {
            Write-Host "Удаляю: $($_.Name)" -ForegroundColor Yellow
            Remove-Item $_.PSPath -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

# 2. Принудительно сканируем новое оборудование
Write-Host "Сканирую новое оборудование..." -ForegroundColor Green
pnputil /scan-devices

# 3. Ждем
Start-Sleep -Seconds 5

# 4. Проверяем
$jlinks = Get-PnpDevice | Where-Object {$_.FriendlyName -like "*J-Link*"}
if ($jlinks) {
    Write-Host "✅ Устройства восстановлены!" -ForegroundColor Green
} else {
    Write-Host "❌ Требуется физическое переподключение USB" -ForegroundColor Red
}
'''

print("⚠ Этот метод удалит J-Link из системы и заставит Windows переустановить драйверы.")
confirm = input("Точно продолжить? (y/n): ")

if confirm.lower() == 'y':
    subprocess.run(["powershell", "-Command", ps_hard_reset], shell=True)
else:
    print("Отменено")
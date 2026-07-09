[app]

# Название приложения (может быть на любом языке)
title = Vim Hof Breath

# Имя пакета и домен — только ASCII, латиница
package.name = breathwimhof
package.domain = org.mori

# Исходники берём из корня; точка входа — main.py
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,wav

# В APK не тащим десктопные tkinter-версии и артефакты сборки
source.exclude_patterns = breath_timer.py,practice_timer.py,BreathWimHof.spec,docs/*,build/*,dist/*,.venv/*

version = 2.0.0

# ВАЖНО: pyttsx3 сюда НЕ добавляем — под Android драйвера нет, сборка упадёт.
# Голос на Android потребует Android TextToSpeech (pyjnius/plyer) — отдельная задача.
requirements = python3,kivy==2.3.1

orientation = portrait
fullscreen = 0

# Современные телефоны — arm64-v8a. Добавь armeabi-v7a, если нужен старый девайс
# (удвоит время сборки).
android.archs = arm64-v8a

android.allow_backup = True

[buildozer]

log_level = 2
warn_on_root = 1

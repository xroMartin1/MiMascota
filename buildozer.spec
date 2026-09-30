[app]
title = PetCare
package.name = petcare
package.domain = org.petcareapp
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json,ttf
source.exclude_dirs = .venv,venv,.kivy,.buildozer,bin,previews,tests,tools,data,__pycache__
source.exclude_patterns = *.pyc,*~
version = 0.1.0
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,requests,certifi
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1

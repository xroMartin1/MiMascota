[app]
title = Mi Mascota
package.name = mimascota
package.domain = org.mimascota
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,json,ttf
source.exclude_dirs = .venv,venv,.kivy,.buildozer,bin,previews,tests,tools,data,__pycache__,supabase
source.exclude_patterns = *.pyc,*~,exp_*.png,test_render*.png,proper_screen*.png,real_screen*.png,shot*.png,google-services.json,android/build_hook.py
version = 0.2.6
icon.filename = assets/brand/icono-app.png
icon.adaptive_foreground.filename = assets/brand/icono-adaptive.png
icon.adaptive_background.filename = assets/brand/icono-background.png
presplash.filename = assets/brand/arranque.png
android.presplash_color = #103D49
requirements = python3,kivy==2.3.1,kivymd==1.2.0,pillow,requests,certifi,segno==1.6.6,pyjnius==1.9.0,tzdata==2026.5,reportlab==4.4.10
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,POST_NOTIFICATIONS
android.api = 36
android.minapi = 24
android.enable_androidx = True
android.manifest.intent_filters = android/auth-intent.xml
android.manifest.launch_mode = singleTask
p4a.hook = android/build_hook.py
p4a.local_recipes = android/recipes
android.add_src = android/src
android.add_resources = android/res/values:values,android/res/drawable:drawable,android/res/xml:xml
android.gradle_dependencies = com.google.firebase:firebase-messaging:25.1.3,com.google.firebase:firebase-analytics:23.2.0
android.add_compile_options = "sourceCompatibility = 1.8", "targetCompatibility = 1.8"
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1

[app]
title = AK PhotoCode
package.name = akphotocode
package.domain = com.akyasir
source.dir = .
source.include_exts = py,png,jpg,jpeg
version = 1.0.0
requirements = python3,kivy==2.3.2,pillow,numpy,plyer,pyjnius
orientation = portrait
fullscreen = 0

android.permissions = READ_MEDIA_IMAGES,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 36
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a
android.accept_sdk_license = True
android.release_artifact = aab

p4a.branch = develop

[buildozer]
log_level = 2
warn_on_root = 1

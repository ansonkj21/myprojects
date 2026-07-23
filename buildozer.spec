[app]
title = UK Trip Planner
package.name = uktripplanner
package.domain = org.example

source.dir = .
source.include_exts = py,kv,png,jpg,atlas
source.include_patterns = trip_data.json

version = 0.1
requirements = python3,kivy==2.3.0,kivy_garden.mapview,requests,plyer

# Permissions: internet for search + map tiles, location for GPS-based
# category search distance sorting
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1

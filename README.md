# UK Trip Planner — First Release

Scope for this release, kept deliberately small:
- **Map** (OpenStreetMap tiles via `kivy_garden.mapview` — no map billing/quota)
- **Location finder** — search bar for an address, postcode, or named place
- **Category browsing** — Attractions / Petrol Pumps / Restaurants buttons
  find nearby places around the device's actual current GPS location
  (falls back to the map's center if no GPS fix is available, e.g. on
  desktop). Results are sorted nearest-first and grouped into 1-mile
  bands: "0.1 - 1 mile", "1.1 - 2 miles", "2.1 - 3 miles", and so on.
- **Pin locations to days** — Day 1, Day 2, Day 3 by default, add more freely
- Pins **persist locally** between app runs (saved as JSON)

Not in this release (candidates for the next one): route ordering, arrival
time estimates, AI-written itinerary summaries, marker colors per day.

## Building the APK without a powerful laptop

Building an Android APK needs the Android SDK/NDK (several GB) and native
compilation — that's the part that struggles on low-spec machines.
**Running the app in desktop mode does not** (`python main.py` uses only
Kivy, which is lightweight), so you can still develop/test locally.

For the actual APK build, use one of these instead of your own machine:

### Option 1 — GitHub Actions (recommended, free)
This project includes `.github/workflows/build-apk.yml`, which builds the
APK on GitHub's cloud runners automatically.
1. Create a free GitHub account and a new repository
2. Push this project's files to it (including the `.github` folder)
3. Go to the repo's **Actions** tab — the build starts automatically
4. When it finishes (~15-20 min first run), download the APK from the
   run's **Artifacts** section
No local Android build tools required at all.

### Option 2 — Google Colab
Colab gives you a free cloud Linux machine in your browser. Upload the
project files, then in a Colab cell:
```python
!pip install buildozer cython
!apt-get install -y openjdk-17-jdk
# cd into your uploaded project folder, then:
!buildozer android debug
```
Session timeouts mean this can be less reliable for long builds than
GitHub Actions, but it works well for quick iterations.

### Option 3 — Gitpod / GitHub Codespaces
Both give you a free cloud dev environment with a terminal — run the
same `pip install buildozer cython && buildozer android debug` commands
there instead of locally.

## 1. Get a Google API key (used only for the search box)
1. Go to https://console.cloud.google.com/
2. Enable **Places API** and **Geocoding API**
3. Create an API key (restrict it to those two APIs)

The map itself uses free OpenStreetMap tiles and needs no key.

## 2. Run on desktop (development)
```bash
pip install -r requirements.txt
export GOOGLE_PLACES_API_KEY="your_key_here"
python main.py
```

## 3. Build the Android APK
```bash
pip install buildozer cython
buildozer -v android debug
buildozer android deploy run   # installs + launches on a connected device
```

## 4. Secure your API key before a real release
Don't hardcode your key into `config.py` before shipping — anyone can
decompile the APK and pull it out. Build a tiny backend that holds the
key and proxies requests, then set `GOOGLE_PLACES_PROXY_URL` in
`config.py` to point at it. For local testing, the `GOOGLE_PLACES_API_KEY`
env var is fine.

## How it works
- Type in the search box → results appear as a list, map recenters on
  the first hit
- Or tap **Attractions / Petrol Pumps / Restaurants** to find nearby
  places (8km radius) around your current GPS location — listed nearest
  first, grouped under distance-band headers (0.1-1 mile, 1.1-2 miles, etc.)
- Pick a day with the day spinner, or tap **+ Day** for a new one
- Tap **Pin to Day N** on a search result to add it to that day
- The pin list below the map shows/removes pins for whichever day is
  selected; all pins across all days show as markers on the map
- Data is saved to `<user_data_dir>/trip_data.json` automatically

## Project structure
```
main.py               Kivy App: search, day selection, pin & marker logic
uktrip.kv              UI layout (Kivy language)
places_service.py      Location search (Places Text Search + Geocoding fallback)
day_manager.py          Day/pin data model + local JSON persistence
config.py              API keys & app settings
buildozer.spec          Android packaging config
requirements.txt        Python dependencies
```

## Known limitation in this release
All markers currently render in the same default pin style regardless of
day — `config.DAY_MARKER_COLORS` already defines a color per day for
when custom marker images are added (`kivy_garden.mapview`'s `MapMarker`
needs a per-color image source, which isn't wired up yet). Today, tell
days apart via the pin list under the map instead of marker color.

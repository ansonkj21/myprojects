"""
Manages the trip's days (Day 1, Day 2, Day 3, ... up to config.MAX_DAYS)
and the pinned locations assigned to each day. Persists to a local JSON
file so a trip survives closing/reopening the app.
"""

import json
import os

import config


class DayManager:
    def __init__(self, storage_path):
        """
        storage_path: full path to a JSON file (use App.user_data_dir so
        it works correctly on Android, e.g.
        os.path.join(app.user_data_dir, "trip_data.json")).
        """
        self.storage_path = storage_path
        self.days = []  # list of {"name": "Day 1", "pins": [ {name,address,lat,lng} ]}
        self._load()
        if not self.days:
            for i in range(1, config.DEFAULT_NUM_DAYS + 1):
                self.days.append({"name": f"Day {i}", "pins": []})
            self._save()

    # ---------- persistence ----------

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    self.days = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.days = []

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(self.days, f, indent=2)
        except OSError:
            pass  # non-fatal — trip just won't persist this run

    # ---------- day management ----------

    def day_names(self):
        return [d["name"] for d in self.days]

    def add_day(self):
        if len(self.days) >= config.MAX_DAYS:
            return None
        new_name = f"Day {len(self.days) + 1}"
        self.days.append({"name": new_name, "pins": []})
        self._save()
        return new_name

    def remove_day(self, day_name):
        self.days = [d for d in self.days if d["name"] != day_name]
        self._save()

    def day_index(self, day_name):
        for i, d in enumerate(self.days):
            if d["name"] == day_name:
                return i
        return -1

    def marker_color(self, day_name):
        idx = self.day_index(day_name)
        if idx < 0:
            return config.DAY_MARKER_COLORS[0]
        return config.DAY_MARKER_COLORS[idx % len(config.DAY_MARKER_COLORS)]

    # ---------- pin management ----------

    def pins_for_day(self, day_name):
        for d in self.days:
            if d["name"] == day_name:
                return d["pins"]
        return []

    def all_pins(self):
        """Every pin across every day, each tagged with its day name — used to draw all markers on the map."""
        out = []
        for d in self.days:
            for pin in d["pins"]:
                out.append({**pin, "day": d["name"]})
        return out

    def add_pin(self, day_name, place):
        """place: dict with name, address, lat, lng."""
        for d in self.days:
            if d["name"] == day_name:
                d["pins"].append({
                    "name": place["name"],
                    "address": place.get("address", ""),
                    "lat": place["lat"],
                    "lng": place["lng"],
                })
                self._save()
                return True
        return False

    def remove_pin(self, day_name, pin_index):
        for d in self.days:
            if d["name"] == day_name and 0 <= pin_index < len(d["pins"]):
                d["pins"].pop(pin_index)
                self._save()
                return True
        return False

    def move_pin(self, from_day, pin_index, to_day):
        pins = self.pins_for_day(from_day)
        if not (0 <= pin_index < len(pins)):
            return False
        pin = pins.pop(pin_index)
        added = self.add_pin(to_day, pin)
        self._save()
        return added

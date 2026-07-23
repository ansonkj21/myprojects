"""
UK Trip Planner — first release.

Scope: search for a location, view it on a map, and pin it to Day 1,
Day 2, Day 3, or however many days the trip needs. Pins persist locally
between app runs.

Run on desktop for development:
    pip install -r requirements.txt
    python main.py

Package for Android:
    buildozer -v android debug
"""

import os

from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

from kivy_garden.mapview import MapMarker

import config
import places_service
from day_manager import DayManager

Builder.load_file("uktrip.kv")


class BandHeader(Label):
    """Section header row shown between distance bands, e.g. '1.1 - 2 miles'."""

    def __init__(self, label_text, **kwargs):
        super().__init__(text=label_text, size_hint_y=None, height=28,
                          bold=True, font_size="13sp", halign="left", **kwargs)


class ResultRow(BoxLayout):
    """One row in the search-results list: name/address + 'Pin here' button."""

    def __init__(self, place, app, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=44,
                          spacing=8, **kwargs)
        self.place = place
        self.app = app

        text = place["name"]
        if place.get("distance_miles") is not None:
            text += f"  ({place['distance_miles']} mi)"
        if place.get("rating"):
            text += f"  ⭐ {place['rating']}"
        if place.get("address") and place["address"] != place["name"]:
            text += f"\n{place['address']}"
        self.add_widget(Label(text=text, font_size="12sp", halign="left"))

        pin_btn = Button(text=f"Pin to {app.current_day}", size_hint_x=None, width=140)
        pin_btn.bind(on_release=lambda *_: self.app.pin_result(self.place))
        self.add_widget(pin_btn)


class PinRow(BoxLayout):
    """One row in the current day's pin list: name + remove button."""

    def __init__(self, pin, index, app, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=44,
                          spacing=8, **kwargs)
        text = pin["name"]
        if pin.get("address") and pin["address"] != pin["name"]:
            text += f"\n{pin['address']}"
        self.add_widget(Label(text=text, font_size="12sp", halign="left"))

        remove_btn = Button(text="Remove", size_hint_x=None, width=90)
        remove_btn.bind(on_release=lambda *_: app.remove_pin(index))
        self.add_widget(remove_btn)


class UKTripApp(App):
    status_message = StringProperty("")
    search_results = ListProperty([])
    day_names = ListProperty([])
    current_day = StringProperty("Day 1")

    map_lat = NumericProperty(config.DEFAULT_MAP_LAT)
    map_lng = NumericProperty(config.DEFAULT_MAP_LNG)
    map_zoom = NumericProperty(config.DEFAULT_MAP_ZOOM)

    # Real device GPS coordinates, once available (falls back to map
    # center until then — see _resolve_user_location).
    user_lat = NumericProperty(0)
    user_lng = NumericProperty(0)
    has_gps_fix = BooleanProperty(False)

    def build(self):
        self.title = "UK Trip Planner"
        storage_path = os.path.join(self.user_data_dir, "trip_data.json")
        self.day_mgr = DayManager(storage_path)
        self.day_names = self.day_mgr.day_names()
        self.current_day = self.day_names[0]
        self._map_markers = []
        self._current_bands = None
        root = Builder.load_file("uktrip.kv")
        Clock.schedule_once(lambda dt: self._refresh_map_markers(), 0.2)
        Clock.schedule_once(lambda dt: self._refresh_pin_list(), 0.2)
        Clock.schedule_once(lambda dt: self.refresh_gps_location(), 0.2)
        return root

    # ---------- location ----------

    def refresh_gps_location(self):
        """
        Try to get a real device GPS fix via plyer. On success, category
        searches will be centered/sorted on this real location instead of
        the map's center. Fails gracefully on desktop or if permission is
        denied — category search then falls back to the map center.
        """
        try:
            from plyer import gps

            def on_location(**kwargs):
                lat, lng = kwargs.get("lat"), kwargs.get("lon")
                if lat and lng:
                    self.user_lat = lat
                    self.user_lng = lng
                    self.has_gps_fix = True
                    self.status_message = ""
                gps.stop()

            def on_status(stype, status):
                pass

            gps.configure(on_location=on_location, on_status=on_status)
            gps.start(minTime=1000, minDistance=1)
            self.status_message = "Getting your location..."
        except (NotImplementedError, ImportError, ModuleNotFoundError):
            # e.g. running on desktop during development — no GPS available
            self.has_gps_fix = False

    def _resolve_user_location(self):
        """The point category search is centered/sorted on: a real GPS fix
        if we have one, otherwise wherever the map is currently showing."""
        if self.has_gps_fix:
            return self.user_lat, self.user_lng
        return self.map_lat, self.map_lng

    # ---------- search ----------

    def do_search(self, query):
        query = query.strip()
        if not query:
            self.status_message = "Type something to search."
            return
        self.status_message = "Searching..."
        Clock.schedule_once(lambda dt: self._do_search(query), 0)

    def _do_search(self, query):
        try:
            results = places_service.search_location(query)
        except places_service.PlacesServiceError as e:
            self.status_message = str(e)
            return

        if not results:
            self.status_message = f"No results for '{query}'."
            self.search_results = []
            self._current_bands = None
            self._populate_results([])
            return

        self.status_message = ""
        self.search_results = results
        self._current_bands = None
        self._populate_results(results)

        # Recenter the map on the first result
        first = results[0]
        self.map_lat = first["lat"]
        self.map_lng = first["lng"]
        self.map_zoom = 13

    def search_category(self, category):
        """Find nearby Attractions/Petrol Pumps/Restaurants around the
        user's actual current GPS location (falls back to map center if
        no GPS fix is available)."""
        self.status_message = f"Finding {category.lower()}..."
        Clock.schedule_once(lambda dt: self._do_search_category(category), 0)

    def _do_search_category(self, category):
        origin_lat, origin_lng = self._resolve_user_location()
        try:
            results = places_service.search_nearby(origin_lat, origin_lng, category)
        except places_service.PlacesServiceError as e:
            self.status_message = str(e)
            return

        if not results:
            self.status_message = f"No {category.lower()} found nearby."
            self.search_results = []
            self._current_bands = None
            self._populate_results([])
            return

        self.status_message = ""
        self.search_results = results
        self._current_bands = places_service.group_by_distance_band(results)
        self._populate_results(results)

    def _populate_results(self, results):
        container = self.root.ids.results_list
        container.clear_widgets()

        # Category searches (which have distance_miles) render grouped by
        # 1-mile band, nearest first; plain text searches render as a flat list.
        if self._current_bands and results and results[0].get("distance_miles") is not None:
            for band_label, places in self._current_bands:
                container.add_widget(BandHeader(band_label))
                for place in places:
                    container.add_widget(ResultRow(place, self))
        else:
            for place in results:
                container.add_widget(ResultRow(place, self))

    # ---------- day management ----------

    def select_day(self, day_name):
        self.current_day = day_name
        self._refresh_pin_list()
        self._refresh_map_markers()
        # Refresh "Pin to X" labels in any currently shown search results
        self._populate_results(self.search_results)

    def add_day(self):
        new_day = self.day_mgr.add_day()
        if new_day is None:
            self.status_message = f"Max {config.MAX_DAYS} days reached."
            return
        self.day_names = self.day_mgr.day_names()
        self.select_day(new_day)

    # ---------- pins ----------

    def pin_result(self, place):
        self.day_mgr.add_pin(self.current_day, place)
        self.status_message = f"Pinned to {self.current_day}."
        self._refresh_pin_list()
        self._refresh_map_markers()

    def remove_pin(self, index):
        self.day_mgr.remove_pin(self.current_day, index)
        self._refresh_pin_list()
        self._refresh_map_markers()

    def _refresh_pin_list(self):
        container = self.root.ids.pins_list
        container.clear_widgets()
        pins = self.day_mgr.pins_for_day(self.current_day)
        if not pins:
            container.add_widget(Label(text="No pins yet for this day.",
                                        size_hint_y=None, height=40))
            return
        for i, pin in enumerate(pins):
            container.add_widget(PinRow(pin, i, self))

    def _refresh_map_markers(self):
        """Draw every pin from every day on the map (all in one color for
        this first release — see README for the planned day-color upgrade)."""
        mapview = self.root.ids.mapview

        for m in self._map_markers:
            mapview.remove_marker(m)
        self._map_markers = []

        for pin in self.day_mgr.all_pins():
            marker = MapMarker(lat=pin["lat"], lon=pin["lng"])
            mapview.add_marker(marker)
            self._map_markers.append(marker)


if __name__ == "__main__":
    UKTripApp().run()

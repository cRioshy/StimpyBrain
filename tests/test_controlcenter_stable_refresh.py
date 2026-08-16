import unittest
from pathlib import Path


ROOT=Path(__file__).parents[1]/"stimpy"/"static"


class ControlcenterStableRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"controlcenter.html").read_text(encoding="utf-8")
        cls.css=(ROOT/"controlcenter.css").read_text(encoding="utf-8")
        cls.js=(ROOT/"controlcenter.js").read_text(encoding="utf-8")

    def test_live_follow_is_visible_and_off_in_markup(self):
        self.assertIn('id="liveFollowButton"',self.html);self.assertIn("LIVE FOLLOW: AUS",self.html);self.assertIn('aria-pressed="false"',self.html)
    def test_live_follow_is_local_only(self):
        self.assertIn("localStorage",self.js);self.assertIn("stimpy.controlcenter.liveFollow",self.js)
    def test_refresh_has_no_page_reload(self):
        self.assertNotIn("location.reload",self.js);self.assertNotIn("window.location.reload",self.js)
    def test_refresh_is_non_overlapping(self):
        self.assertIn("state.refreshing",self.js);self.assertIn("if(state.refreshing)return",self.js)
    def test_window_and_container_scroll_are_preserved(self):
        self.assertIn("window.scrollX",self.js);self.assertIn("window.scrollY",self.js);self.assertIn("scrollLeft",self.js);self.assertIn("scrollTop",self.js)
    def test_filters_and_focus_are_preserved(self):
        self.assertIn('search:byId("searchInput").value',self.js);self.assertIn('filter:byId("statusFilter").value',self.js);self.assertIn("preventScroll:true",self.js)
    def test_rows_have_stable_ids_and_are_patched(self):
        self.assertIn("dataset.rowId",self.js);self.assertIn("patchChildren",self.js);self.assertIn("patchRegion",self.js)
    def test_important_events_only_drive_follow(self):
        self.assertIn('importantChange("trades"',self.js);self.assertIn('importantChange("positions"',self.js);self.assertIn('importantChange("social"',self.js);self.assertNotIn('importantChange("decisions"',self.js)
    def test_manual_scroll_has_five_second_cooldown(self):
        self.assertIn("Date.now()-state.manualScrollAt<5000",self.js);self.assertIn('window.addEventListener("scroll"',self.js)
    def test_reconnect_keeps_rendered_content(self):
        marker='Verbindung unterbrochen · Daten bleiben sichtbar';self.assertIn(marker,self.js);self.assertNotIn('byId("detail").replaceChildren(el("p","error",`Controlcenter nicht verfügbar',self.js)
    def test_dom_limits_are_bounded(self):
        self.assertIn("feed.items.slice(0,200)",self.js);self.assertIn("decisions.items.slice(0,100)",self.js);self.assertIn("trades.items.slice(0,100)",self.js)
    def test_new_and_updated_rows_are_transiently_marked(self):
        self.assertIn("row-new",self.css);self.assertIn("row-updated",self.css);self.assertNotIn("infinite",self.css)


if __name__=="__main__":unittest.main()

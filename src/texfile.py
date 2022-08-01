import gi
from gi.repository import GObject, GtkSource, Gio
import os

"""
  Keeps name of the opened tex file, its root tex document
  Helps to find the log files, etc.
"""

class TexFile(GtkSource.File):
    __gtype_name__ = "TexFile"

    __gsignals__ = {
        'changed': (GObject.SIGNAL_RUN_FIRST, None, ())
    }

    def __init__(self):
        super().__init__()
        self.monitor = None
        self.monitor_cb_id = None

    def set_path(self,path):
        f = Gio.File.new_for_path(path)
        self.set_location(f)

    def get_title(self):
        location = self.get_location()
        if location is None:
            return "New Document"
        path = location.get_path()
        path = os.path.basename(path)
        return os.path.splitext(path)[0]

    def get_pdf_path(self):
        base = self.get_root_base()
        if base is None:
            return None
        return base + ".pdf"

    def get_log_path(self):
        base = self.get_root_base()
        if base is None:
            return None
        return base + ".log"
        
    def get_tex_path(self):
        location = self.get_location()
        if location is None:
            return None
        return location.get_path()

    def get_dir(self):
        location = self.get_location()
        if location is None:
            return None
        path = location.get_path()
        return os.path.dirname(path)
        
    def get_root(self):
        return self.get_location()

    def get_root_path(self):
        root = self.get_root()
        if root is None:
            return None
        return root.get_path()

    def get_root_base(self):
        path = self.get_root_path()
        if path is None:
            return None
        return os.path.splitext(path)[0]

    def set_location(self, location):
        if self.monitor:
            self.stop_monitor
        super().set_location(location)
        self.start_monitor()

    def start_monitor(self):
        if self.monitor:
            return
        self.monitor = super().get_location().monitor_file(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.monitor.set_rate_limit(500)
        self.monitor_cb_id = self.monitor.connect("changed", lambda *_: self.emit("changed"))

    def stop_monitor(self):
        self.monitor.disconnect(self.monitor_cb_id)
        self.monitor_cb_id = None
        self.monitor = None

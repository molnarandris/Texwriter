from gi.repository import  Gtk

class LogView(Gtk.Box):
    __gtype_name__ = "LogView"

    def __init__(self):
        super().__init__()

        self.set_orientation(Gtk.Orientation.VERTICAL)
        label = Gtk.Label.new("The compilation log")
        self.append(label)


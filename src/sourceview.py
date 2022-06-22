import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GtkSource, GObject

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/sourceview.ui')
class TexwriterSource(Gtk.ScrolledWindow):
    __gtype_name__ = "TexwriterSource"

    GObject.type_register(GtkSource.View)

    #sourceview    = Gtk.Template.Child()

    def __init__(self):
        super().__init__()
        

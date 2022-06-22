import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GtkSource, GObject

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/sourceview.ui')
class TexwriterSource(Gtk.ScrolledWindow):
    __gtype_name__ = "TexwriterSource"

    GObject.type_register(GtkSource.View)

    sourceview    = Gtk.Template.Child()

    filename = GObject.Property(type=str, default='New Document')

    def __init__(self):
        super().__init__()
        self._filename = "New Document"
        
    def synctex_bck(self,sender, line):
        buf = self.sourceview.get_buffer()
        _, it = buf.get_iter_at_line_offset(line-1,0)
        buf.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,True, 0, 0.382)


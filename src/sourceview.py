import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GtkSource, GObject, GLib
from .latexbuffer import LatexBuffer
from .texfile import TexFile

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/sourceview.ui')
class TexwriterSource(Gtk.ScrolledWindow):
    __gtype_name__ = "TexwriterSource"

    GObject.type_register(GtkSource.View)

    sourceview    = Gtk.Template.Child()

    title = GObject.Property(type=str, default='New Document')
    modified = GObject.Property(type=bool, default=False)

    def __init__(self):
        super().__init__()
        buffer = LatexBuffer()
        self.sourceview.set_buffer(buffer)
        buffer.connect("changed", lambda _ : self.set_property("modified", True))
        self.file = TexFile()

    def open_file(self,file):

        def load_finish_cb(loader, result):
            success = loader.load_finish(result)
            path = loader.get_location().get_path()
            if success:
                self.file.tex_path = path
                self.set_property("title", self.file.title)
                self.set_property("modified", False)
            else:
                print("Could not load file: " + path)
            return success

        buffer = self.sourceview.get_buffer()
        loader = GtkSource.FileLoader.new(buffer, file)
        loader.load_async(io_priority = GLib.PRIORITY_DEFAULT, callback = load_finish_cb)


    def synctex_bck(self,sender, line):
        buf = self.sourceview.get_buffer()
        _, it = buf.get_iter_at_line_offset(line-1,0)
        buf.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,True, 0, 0.382)


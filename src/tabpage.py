from gi.repository import Gtk, Gio, GObject
from .sourceview import TexwriterSource
from .pdfviewer import PdfViewer
from .logview import LogView

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/tabpage.ui')
class TabPage(Gtk.Widget):
    __gtype_name__ = 'TabPage'

    paned         = Gtk.Template.Child()
    pdfview       = Gtk.Template.Child()
    logview       = Gtk.Template.Child()
    sourceview    = Gtk.Template.Child()

    busy = GObject.Property(type=bool, default=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

        # Making paned to change size when window is resized
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        # do_dispose does not run
        self.connect("destroy", self.dispose_cb)
        self.connect("realize", self.realize_cb)

    def realize_cb(self, _):
        # hack: set first size
        self.paned.set_position(self.get_root().get_allocated_width() / 2)

    # do_dispose does not run
    def dispose_cb(self, _):
        self.paned.unparent()

    def on_compile_finished(self, proc, result, data):
        self.to_compile = False
        if not proc.get_successful():
            self.logprocessor.run()
        self.set_property("busy", False)

    def compile(self):
        if self.sourceview.file is None:
            return
        if self.sourceview.modified:
            self.to_compile = True
            self.sourceview.save()
            return  # we have to wait for the saving to finish
        self.to_compile = False
        self.sourceview.clear_tags()
        path = self.sourceview.file.get_tex_path()
        directory = self.sourceview.file.get_dir()
        cmd = ['flatpak-spawn', '--host', 'latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', path]
        proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
        self.set_property("busy", True)
        proc.communicate_utf8_async(None, None, self.on_compile_finished, None)


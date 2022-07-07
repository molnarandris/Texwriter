import gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GtkSource, GObject, GLib, Gio
from .latexbuffer import LatexBuffer
from .texfile import TexFile

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/editor_page.ui')
class EditorPage(Gtk.Widget):
    __gtype_name__ = "EditorPage"

    GObject.type_register(GtkSource.View)

    sourceview    = Gtk.Template.Child()

    title = GObject.Property(type=str, default='New Document')
    modified = GObject.Property(type=bool, default=False)


    __gsignals__ = {
        'saved': (GObject.SIGNAL_RUN_LAST, None, (bool,)),
    }


    def __init__(self):
        super().__init__()
        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)
        buffer = LatexBuffer()
        self.sourceview.set_buffer(buffer)
        buffer.connect("changed", lambda _ : self.set_property("modified", True))
        self.file = None
        self.to_compile = False

    def load_finish_cb(self, loader, result, cb):
        success = loader.load_finish(result)
        path = loader.get_location().get_path()
        if success:
            self.file = TexFile()
            self.file.set_location(loader.get_location())
            self.set_property("modified", False)
            self.set_property("title", self.file.get_title())
        else:
            self.file = None
            print("Could not load file: " + path)
        cb(success, self.file)
        return success

    def load_file(self,file, cb):
        buffer = self.sourceview.get_buffer()
        loader = GtkSource.FileLoader.new(buffer, file)
        loader.load_async(io_priority = GLib.PRIORITY_DEFAULT,
                          callback    = self.load_finish_cb,
                          user_data   = cb)


    def save(self, callback = None):
        if self.file is None:
            dialog = Gtk.FileChooserNative.new(
                        "Save File",
                        self.get_root(),
                        Gtk.FileChooserAction.SAVE,
                        None,
                        None
                     )

            filter_tex = Gtk.FileFilter()
            filter_tex.set_name("Latex")
            filter_tex.add_mime_type("text/x-tex")
            dialog.add_filter(filter_tex)

            filter_any = Gtk.FileFilter()
            filter_any.set_name("Any files")
            filter_any.add_pattern("*")
            dialog.add_filter(filter_any)

            dialog.connect("response", self.on_save_response, callback)
            dialog.set_modal(True)
            dialog.show()
            self.save_dialog = dialog
        else:
            buffer = self.sourceview.get_buffer()
            saver = GtkSource.FileSaver.new(buffer, self.file)
            saver.save_async(io_priority = GLib.PRIORITY_DEFAULT,
                             callback = self.save_finish_cb,
                             user_data = callback)

    def on_save_response(self, dialog, response, callback):
        if response != Gtk.ResponseType.ACCEPT:
            self.save_dialog = None
            return
        file = GtkSource.File.new()
        file.set_location(dialog.get_file())
        self.file = file
        self.save_dialog = None
        self.save(callback)


    def save_finish_cb(self, saver, result, callback):
        success = saver.save_finish(result)
        path = saver.get_location().get_path()
        if success:
            self.set_property("modified", False)
            self.emit("saved", True)
        else:
            print("Could not save file: " + path)
            self.emit("saved", False)
        if callback:
            callback()
        return success

    def synctex_bck(self,sender, line):
        buf = self.sourceview.get_buffer()
        _, it = buf.get_iter_at_line_offset(line-1,0)
        buf.place_cursor(it)
        self.sourceview.scroll_to_iter(it,0,True, 0, 0.382)

    def get_pdf_path(self):
        if self.file:
            return self.file.get_pdf_path()
        else:
            return None

    def clear_tags(self):
        self.sourceview.get_buffer().clear_tags()

    def goto(self, line, context, offset):
        """Scrolls to the given line, searches for the string given in context and
        places the cursor at offset inside of the string context.

        :param int line:
            The line to scroll to.
        :param str context:
            The string to look for in the given line.
        :param int offset:
            The offser within str to place the cursor at. If offset is negative, it
            places the cursor to the end, -1 meaning after the last character.
        """

        buffer = self.sourceview.get_buffer()
        begin_it = buffer.get_iter_at_line_offset(line, 0)[1]
        limit_it = buffer.get_iter_at_line_offset(line+1, 0)[1]
        flag = Gtk.TextSearchFlags.TEXT_ONLY
        result = begin_it.forward_search(context, flag, limit_it)
        if result:
            start_it, end_it = result
            if offset >= 0:
                start_it.forward_chars(offset)
                it = start_it
            else:
                end_it.backward_chars(-offset-1)
                it = end_it
        else:
            it = begin_it
        self.sourceview.scroll_to_iter(it, 0.3, False, 0, 0)
        buffer.place_cursor(it)
        self.sourceview.grab_focus()


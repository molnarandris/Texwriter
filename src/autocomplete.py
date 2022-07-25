from gi.repository import Gtk, Gdk


class AutocompletePopover(Gtk.Popover):

    def __init__(self, editor_page):
        super().__init__()
        self.set_parent(editor_page)
        self.editor_page = editor_page
        label = Gtk.Label.new("Hello world")
        self.set_child(label)
        self.view = editor_page.sourceview
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_autohide(False)
        self.set_has_arrow(True)

        eck = Gtk.EventControllerKey.new()
        self.view.add_controller(eck)
        eck.connect("key-released", self.on_insert)

        self.active = False

    def on_insert(self, controller, keyval, keycode, modifier):
        if (keyval is not Gdk.KEY_backslash) and not self.active:
            return

        buf = self.view.get_buffer()
        it = buf.get_iter_at_mark(buf.get_insert())
        buf_rect = self.view.get_iter_location(it)
        rect = Gdk.Rectangle()
        x, y = self.view.buffer_to_window_coords(Gtk.TextWindowType.TEXT, buf_rect.x,buf_rect.y)
        rect.x, rect.y = self.view.translate_coordinates(self.editor_page, x,y)
        rect.width = buf_rect.width
        rect.height = buf_rect.height
        self.set_pointing_to(rect)

        if (keyval is Gdk.KEY_backslash) and not self.active:
            self.active = True
            self.popup()

        if self.active and keyval is Gdk.KEY_Escape:
            self.active = False
            self.popdown()


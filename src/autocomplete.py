from gi.repository import Gtk, Gdk


class AutocompletePopover(Gtk.Popover):

    def __init__(self, editor_page):
        super().__init__()
        self.set_parent(editor_page)
        self.editor_page = editor_page

        #layout = Gtk.BinLayout()
        #self.set_layout_manager(layout)

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        self.set_child(box)
        text = Gtk.Text()
        box.append(text)
        #text.set_visible(False)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        self.view = editor_page.sourceview
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_autohide(True)
        self.set_has_arrow(False)
        self.set_offset(0,5)

        text.get_buffer().connect("inserted-text", self.on_insert)
        self.text = text

        eck = Gtk.EventControllerKey.new()
        self.view.add_controller(eck)
        eck.connect("key-released", self.on_key_released)

    def on_insert(self, entrybuffer, pos, string, len_):
        #print("Hi", string)
        pass

    def on_key_released(self, controller, keyval, keycode, modifier):
        if keyval is Gdk.KEY_backslash:
            self.update_position()
            self.popup()

    def update_position(self):
        buf = self.view.get_buffer()
        it = buf.get_iter_at_mark(buf.get_insert())
        buf_rect = self.view.get_iter_location(it)
        rect = Gdk.Rectangle()
        x, y = self.view.buffer_to_window_coords(Gtk.TextWindowType.TEXT, buf_rect.x,buf_rect.y)
        rect.x, rect.y = self.view.translate_coordinates(self.editor_page, x,y)
        rect.width = buf_rect.width
        rect.height = buf_rect.height
        self.set_pointing_to(rect)
        

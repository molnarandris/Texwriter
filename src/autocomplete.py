from gi.repository import Gtk, Gdk


class AutocompletePopover(Gtk.Popover):

    def __init__(self, editor_page):
        super().__init__()

        self.active = False
        self.string = ""
        self.set_parent(editor_page)
        self.editor_page = editor_page

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL,10)
        self.set_child(box)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        label = Gtk.Label.new("Hello world")
        box.append(label)
        self.view = editor_page.sourceview
        self.set_position(Gtk.PositionType.BOTTOM)
        self.set_autohide(False)
        self.set_has_arrow(False)
        self.set_offset(0,5)

        controller = Gtk.EventControllerKey.new()
        self.view.add_controller(controller)
        controller.connect("key-released", self.on_key_released)

        controller = Gtk.GestureClick.new()
        self.view.add_controller(controller)
        controller.connect("pressed", self.on_view_click)

        buf = self.view.get_buffer()
        buf.connect("insert-text", self.on_insert)

    def deactivate(self):
        if not self.active:
            return
        self.active = False
        self.string = ""
        self.popdown()

    def activate(self):
        if self.active:
            return
        self.active = True
        self.popup()

    def on_insert(self, buffer, it, string, len_):
        if not self.active:
            return
        self.string += string
        print("Hi", self.string)

    def on_key_released(self, controller, keyval, keycode, modifier):
        if keyval == Gdk.KEY_backslash:
            self.activate()
        if keyval == Gdk.KEY_Escape:
            self.deactivate()
        if self.active:
            self.update_position()

    def on_view_click(self, controller, n_press, x, y):
        if self.active:
            self.deactivate()

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
        

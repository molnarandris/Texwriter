import gi, re
gi.require_version('Poppler', '0.18')
from gi.repository import Gtk, GObject, Poppler, Graphene, Gdk, GLib
from .utilities import ProcessRunner


# Currently very stupid: rendering everythin at once and keeping all in memory
@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/pdfviewer.ui')
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    __gsignals__ = {
        'synctex-bck': (GObject.SIGNAL_RUN_FIRST, None, (int,)),
        'loaded' : (GObject.SIGNAL_RUN_FIRST, None, (bool,)),
    }

    stack     = Gtk.Template.Child()
    scroll    = Gtk.Template.Child()
    box       = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.page_sep = 5
        self.doc = None
        self.scale = 1
        self.x = None
        self.y = None
        self.path = None

        layout = Gtk.BinLayout()
        self.set_layout_manager(layout)

        self.stack.set_visible_child_name("empty")

        controller = Gtk.EventControllerScroll()
        controller.connect("scroll", self.on_scroll)
        #controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        self.box.add_controller(controller)

        controller = Gtk.GestureClick()
        controller.connect("pressed", self.on_click)
        controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        self.add_controller(controller)

        # As can't get event coordinates, need to store pointer coordinates
        controller = Gtk.EventControllerMotion()
        controller.connect("motion", self.on_motion)
        self.add_controller(controller)

    def on_motion(self,widget,x,y):
        self.x = x
        self.y = y

    def load(self, path):
        child = self.box.get_first_child()
        while child:
            self.box.remove(child)
            child = self.box.get_first_child()

        print("Opening pdf: ",  path)

        if path is None:
            self.stack.set_visible_child_name("empty")
            return
        self.path = path
        uri = 'file://' + path
        try:
            doc = Poppler.Document.new_from_file(uri)
        except:
           self.stack.set_visible_child_name("empty")
           self.emit("loaded", False)
           return
        for i in range(doc.get_n_pages()):
            pg = PdfPage(doc.get_page(i))
            overlay = Gtk.Overlay()
            overlay.set_child(pg)
            self.box.append(overlay)
        self.doc = doc
        self.stack.set_visible_child_name("pdf")
        self.emit("loaded", True)


    # Far from perfect, but more or less works. Should not render right at zoom.
    def on_scroll(self, controller, dx, dy):
        if not (controller.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
            return Gdk.EVENT_PROPAGATE
        viewport = self.box.get_parent()
        hadj = viewport.get_hadjustment()
        vadj = viewport.get_vadjustment()
        h = hadj.get_value()
        v = vadj.get_value()
        s = 1.05 if dy>0 else 1.0/1.05
        self.scale *= s
        self.x *=s
        self.y *=s
        for child in self.box:
            for c in child:
                c.set_scale(self.scale)
        hadj.set_value((h + self.x) * s - self.x)
        vadj.set_value((v + self.y) * s - self.y)
        return Gdk.EVENT_STOP
    def on_click(self, controller, n, x, y):
        pass

    def synctex_fwd(self, page, x, y, h, v, H, W):
        rect = SynctexRect(W,H,h,v,self.scale)
        overlay = self.get_page(page)
        overlay.add_overlay(rect)
        self.scroll_to(page,y)

    def scroll_to(self, page, y):
        pg = self.get_page(page).get_child()
        point = Graphene.Point()
        point.init(0,y)
        _,p = pg.compute_point(self,point)
        viewport = self.box.get_parent()
        vadj = viewport.get_vadjustment()
        vadj.set_value(p.y-vadj.get_page_size()*0.302)

    def get_page(self,n):
        i = 1
        child = self.box.get_first_child()
        while i<n:
            child = child.get_next_sibling()
            i+=1
        return child


class SynctexRect(Gtk.Widget):
    __gtype_name__ = 'SynctexRect'

    def __init__(self,W,H,h,v,s):
        super().__init__()
        self.width = W
        self.height = H+10
        self.top = v-H-5
        self.start = h
        self.color = Gdk.RGBA()
        self.color.parse("#FFF38080")
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_scale(s)
        GLib.timeout_add(700,self.do_destroy)

    def set_margin(self):
        self.set_margin_top(self.top*self.scale)
        self.set_margin_start(self.start*self.scale)

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.VERTICAL:
            return (self.height*self.scale,self.height*self.scale,-1,-1)
        else:
            return (self.width*self.scale,self.width*self.scale,-1,-1)

    def do_snapshot(self, snapshot):
        rect = Graphene.Rect().init(0, 0, self.get_width(), self.get_height())
        snapshot.append_color(self.color, rect)

    def set_scale(self,s):
        self.scale = s
        self.set_margin()
        self.queue_resize()

    def do_destroy(self):
        self.unparent()
        return False

class PdfPage(Gtk.Widget):
    __gtype_name__ = 'PdfPage'

    def __init__(self, pg):
        super().__init__()
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.CENTER)
        self.set_tooltip_text("hello world")
        self.pg = pg
        self.scale = 1

        controller = Gtk.GestureClick()
        controller.connect("pressed", self.on_click)
        controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        self.add_controller(controller)

    def on_click(self, controller, n, x,y):

        def on_synctex_finished(sender):
            result = re.search("Line:(.*)", sender.stdout)
            line = int(result.group(1))
            self.get_parent().get_parent().emit("synctex-bck", line)

        if not (controller.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
            return Gdk.EVENT_PROPAGATE
        arg = str(self.pg.get_index()+1) + ":" + str(x/self.scale) + ":" + str(y/self.scale) + ":" + self.get_parent().get_parent().path
        cmd = ['flatpak-spawn', '--host', 'synctex', 'edit', '-o', arg]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_synctex_finished)

        controller.set_state(Gtk.EventSequenceState.CLAIMED)



    def set_scale(self,scale):
        self.scale = scale
        self.queue_resize()

    def do_measure(self, orientation, for_size):
        w,h = self.pg.get_size()
        s = w if orientation == Gtk.Orientation.HORIZONTAL else h
        s = s* self.scale
        return (s,s,-1,-1)

    def do_snapshot(self,snapshot):
        rect = Graphene.Rect().init(0,0,self.get_width(), self.get_height())
        color = Gdk.RGBA()
        color.parse("white")
        snapshot.append_color(color,rect)
        ctx = snapshot.append_cairo(rect)
        ctx.scale(self.scale,self.scale)
        self.pg.render(ctx)




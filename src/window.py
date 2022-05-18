# window.py
#
# Copyright 2022 András Molnár
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os, re
import gi
gi.require_version('GtkSource', '5')
gi.require_version('Poppler', '0.18')
from gi.repository import Gtk, GObject, GtkSource, Gio, GLib, Poppler, Gdk, Graphene


@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    GObject.type_register(GtkSource.View)
    paned        = Gtk.Template.Child()
    sourceview   = Gtk.Template.Child()
    header_bar   = Gtk.Template.Child()
    pdfview      = Gtk.Template.Child()
    title        = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Save and restore window geometry
        settings = Gio.Settings.new(
            "com.github.molnarandris.texwriter"
        )
        settings.bind("width", self, "default-width", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("height", self, "default-height", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("maximized", self, "maximized", Gio.SettingsBindFlags.DEFAULT)
        settings.bind("paned-position", self.paned, "position", Gio.SettingsBindFlags.DEFAULT)

        # Making paned to change size when window is resized
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        actions = [
            ('open', self.on_open_action, ['<primary>o']),
            ('close', self.on_close_action, ['<primary>w']),
            ('save', self.on_save_action, ['<primary>s']),
            ('compile', self.on_compile_action, ['F5']),
            ('synctex-fwd', self.synctex_fwd, ['F7']),
        ]

        for a in actions: self.create_action(*a)

        manager = GtkSource.LanguageManager()
        language = manager.get_language("latex")
        buffer = self.sourceview.get_buffer()
        buffer.set_language(language)
        buffer.connect("changed", lambda _: self.title.set_saved(False))

        self.file = None

    def synctex_fwd(self, sender, _):
        def on_synctex_finished(sender):
            result = re.search("Page:(.*)", sender.stdout)
            page = int(result.group(1))
            result = re.search("x:(.*)", sender.stdout)
            x = float(result.group(1))
            result = re.search("y:(.*)", sender.stdout)
            y = float(result.group(1))
            result = re.search("h:(.*)", sender.stdout)
            h = float(result.group(1))
            result = re.search("v:(.*)", sender.stdout)
            v = float(result.group(1))
            result = re.search("H:(.*)", sender.stdout)
            H = float(result.group(1))
            result = re.search("W:(.*)", sender.stdout)
            W = float(result.group(1))
            self.pdfview.synctex_fwd(page,x,y,h,v,H,W)

        buf = self.sourceview.get_buffer()
        it = buf.get_iter_at_mark(buf.get_insert())
        pos = str(it.get_line()) + ":" + str(it.get_line_offset()) + ":" + self.file.get_location().get_path()
        path, _ = os.path.splitext(self.file.get_location().get_path())
        path = path + '.pdf'
        cmd = ['flatpak-spawn', '--host', 'synctex', 'view', '-i', pos, '-o', path]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_synctex_finished)

    def open_file(self,file):

        def load_finish_cb(loader, result):
            success = loader.load_finish(result)
            path = loader.get_location().get_path()
            if success:
                self.file = file # when we call this fcn, file is the right thing
                self.title.set_saved(True)
                s,t = os.path.split(path)
                self.title.set_title_string(t)
                self.title.set_subtitle_string(s)
            else:
                print("Could not load file: " + path)
            return success

        buffer = self.sourceview.get_buffer()
        loader = GtkSource.FileLoader.new(buffer, file)
        loader.load_async(io_priority=GLib.PRIORITY_DEFAULT, callback = load_finish_cb)
        path, _ = os.path.splitext(file.get_location().get_path())
        path = path + '.pdf'
        self.pdfview.open_file(path)


    def on_open_action(self, widget, _):

        # Extra reference to dialog to prevent garbage collection
        def dialog_response(dialog, response, _dialog):
            if response == Gtk.ResponseType.ACCEPT:
                file = GtkSource.File.new()
                file.set_location(dialog.get_file())
                self.open_file(file)

        dialog = Gtk.FileChooserNative.new( "Open file", self, Gtk.FileChooserAction.OPEN, None, None)
        dialog.connect("response", dialog_response, dialog)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        dialog.show()

    def save_file(self, buffer, file):

        def save_finish_cb(saver, result):
            success = saver.save_finish(result)
            path = saver.get_location().get_path()
            if success:
                self.title.set_saved(True)
            else:
                print("Could not save file: " + path)
            return success

        saver = GtkSource.FileSaver.new(buffer = buffer, file = file)
        saver.save_async(io_priority = GLib.PRIORITY_DEFAULT, callback = save_finish_cb)

    def on_save_action(self, widget, _):

        def dialog_response(self, dialog, response, _dialog):
            if response == Gtk.ResponseType.ACCEPT:
                file = GtkSource.File.new()
                file.set_location(dialog.get_file())
                self.save_file(file)

        if self.file is not None:
            buffer = self.sourceview.get_buffer()
            self.save_file(buffer, self.file)
            return
        dialog = Gtk.FileChooserNative.new( "Save file", self, Gtk.FileChooserAction.SAVE, None, None)
        dialog.connect("response", dialog_response, dialog)

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Text files")
        filter_text.add_mime_type("text/plain")
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

        dialog.show()

    def on_close_action(self, widget, _):
        print("close file")

    def on_compile_action(self, widget, _):
        def on_compile_finished(sender):
            if sender.result == 0:
                # Compilation was successful
                print("Successfully compiled")
                tex = self.file.get_location().get_path()
                pdf,_  = os.path.splitext(tex)
                self.pdfview.open_file(pdf+".pdf")
            else:
                # Compilation failed
                print("Compile failed")

        print("compiling")
        tex = self.file.get_location().get_path()
        directory = os.path.dirname(tex)
        cmd = ['flatpak-spawn', '--host', '/usr/bin/latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', '-halt-on-error', '-output-directory=' + directory, tex]
        proc = ProcessRunner(cmd)
        proc.connect('finished', on_compile_finished)

    def create_action(self, name, callback, shortcuts=None):
        """Add a window action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.get_application().set_accels_for_action(f"win.{name}", shortcuts)

class ProcessRunner(GObject.GObject):

    __gsignals__ = {
        'finished': (GObject.SIGNAL_RUN_LAST, None, ()),
    }


    def __init__(self,cmd):
        super().__init__()

        self.proc = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE|Gio.SubprocessFlags.STDERR_PIPE)
        self.cancellable = Gio.Cancellable.new()
        self.proc.communicate_utf8_async(None, self.cancellable, self.callback, None)
        self.result = None
        self.stdout = None
        self.stderr = None

    def callback(self,sucprocess: Gio.Subprocess, result: Gio.AsyncResult, data):
        try:
            _, self.stdout, self.stderr = self.proc.communicate_utf8_finish(result)
            self.result = self.proc.get_exit_status()
            self.emit('finished')
        except GLib.Error as err:
            if err.domain == 'g-io-error-quark':
                return

    def cancel(self):
        self.cancellable.cancel()




# Currently very stupid: rendering everythin at once and keeping all in memory
class PdfViewer(Gtk.Widget):
    __gtype_name__ = 'PdfViewer'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.page_sep = 5
        self.doc = None
        self.scale = 1
        self.x = None
        self.y = None

        self.set_valign(Gtk.Align.CENTER)
        self.set_halign(Gtk.Align.CENTER)
        self.set_margin_top(10)
        self.set_margin_bottom(10)

        layout = Gtk.BoxLayout()
        layout.set_orientation(Gtk.Orientation.VERTICAL)
        layout.set_spacing(10)
        self.set_layout_manager(layout)

        controller = Gtk.EventControllerScroll()
        controller.connect("scroll", self.on_scroll)
        #controller.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        self.add_controller(controller)

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

    # currently not working...
    def do_dispose(self):
        child = self.get_first_child()
        while child:
            child.unparent()
            child = self.get_first_child()
        super().do_dispose()

    def open_file(self, path):
        child = self.get_first_child()
        while child:
            child.unparent()
            child = self.get_first_child()
        uri = 'file://' + path
        try:
            doc = Poppler.Document.new_from_file(uri)
        except:
           print("No pdf file")
           return
        for i in range(doc.get_n_pages()):
            overlay = Gtk.Overlay()
            overlay.set_parent(self)
            pg = PdfPage(doc.get_page(i))
            overlay.set_child(pg)
        self.doc = doc


    # Far from perfect, but more or less works. Should not render right at zoom.
    def on_scroll(self, controller, dx, dy):
        if not (controller.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
            return Gdk.EVENT_PROPAGATE
        viewport = self.get_parent()
        hadj = viewport.get_hadjustment()
        vadj = viewport.get_vadjustment()
        h = hadj.get_value()
        v = vadj.get_value()
        x = self.x - h
        y = self.y - v
        if dy>0:
            self.scale *= 1.05
            h = self.x*1.05 - x
            v = self.y*1.05 - y
            self.x *=1.05
            self.y *=1.05
        else:
            self.scale /= 1.05
            h = self.x/1.05 - x
            v = self.y/1.05 - y
            self.x/=1.05
            self.y/=1.05
        for child in self:
            for c in child:
                c.set_scale(self.scale)
        hadj.set_value(h)
        vadj.set_value(v)
        return Gdk.EVENT_STOP

    def on_click(self, controller, n, x, y):
        print("Pdf Click!", x, y)

    def synctex_fwd(self, page, x, y, h, v, H, W):
        print(page, x, y, h, v, H, W)
        rect = SynctexRect(W,H,h,v,self.scale)
        overlay = self.get_page(page)
        overlay.add_overlay(rect)

    def get_page(self,n):
        i = 1
        child = self.get_first_child()
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
        print("Page click!", self.pg.get_index(), x, y)
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

class TitleWidget(Gtk.Box):
    __gtype_name__ = "TitleWidget"

    def __init__(self):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.set_valign(Gtk.Align.CENTER)
        self.title = Gtk.Label()
        self.subtitle = Gtk.Label()
        self.saved = True
        self.set_title_string("New Document")
        self.set_subtitle_string("path")

        self.append(self.title)
        self.append(self.subtitle)


    def set_title_string(self,s):
        self.title_string = s
        if self.saved:
            self.title.set_markup("<b>" + s + "</b>")
        else:
            self.title.set_markup("<it><b>" + s + "</b></it>")

    def set_subtitle_string(self,s):
        self.subtitle_string = s
        self.subtitle.set_markup("<small>" + s + "</small>")

    def set_saved(self,b):
        self.saved = b
        if self.saved:
            self.title.set_markup("<b>" + self.title_string + "</b>")
        else:
            self.title.set_markup("<i><b>" + self.title_string + "</b></i>")

class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent):
        Gtk.AboutDialog.__init__(self)
        self.props.program_name = 'texwriter'
        self.props.version = "0.1.0"
        self.props.authors = ['András Molnár']
        self.props.copyright = '2022 András Molnár'
        self.props.logo_icon_name = 'com.github.molnarandris.texwriter'
        self.props.modal = True
        self.set_transient_for(parent)

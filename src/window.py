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

import os, re, gi
gi.require_version('GtkSource', '5')
from gi.repository import Gtk, GObject, GtkSource, Gio, GLib, Gdk, Adw
from .pdfviewer import PdfViewer
from .utilities import ProcessRunner
from .documentmanager import  DocumentManager
from .logview import LogView
from .sourceview import TexwriterSource

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    paned         = Gtk.Template.Child()
    pdfview       = Gtk.Template.Child()
    title         = Gtk.Template.Child()
    btn_stack     = Gtk.Template.Child()
    logview       = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    texstack      = Gtk.Template.Child()
    tab_view      = Gtk.Template.Child()

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
            ('close', self.on_close_tab, ['<primary>w']),
            ('save', self.on_save_action, ['<primary>s']),
            ('compile', self.on_compile_action, ['F5']),
            #('synctex-fwd', self.synctex_fwd, ['F7']),
            ('cancel', self.on_cancel_action, []),
            ('new-tab', lambda *_: self.create_new_tab(), []),
        ]

        for a in actions: self.create_action(*a)
        self.texstack.set_visible_child_name("empty")

        #docmanager = DocumentManager(buffer)
        #docmanager.connect("open-success", self.open_success_cb)
        #docmanager.connect("save-success", lambda _: self.title.set_saved(True))
        #docmanager.connect("open-pdf", self.open_pdf)
        #docmanager.connect("compiled", self.on_compiled)

        #self.docmanager = docmanager

        #self.pdfview.connect("synctex-bck", self.synctex_bck)

    def set_pg_modified(self, b, pg):
        ''' Sets the icon of a given tab page
        '''
        if b:
            icon = Gio.ThemedIcon.new("document-modified-symbolic")
            pg.set_icon(icon)
        else:
            pg.set_icon(None)

    def create_new_tab(self):
        src = TexwriterSource()
        tab_page = self.tab_view.append(src)
        flag = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        src.bind_property("title", tab_page, "title", flag)
        src.connect("notify::modified", lambda obj, _, pg : self.set_pg_modified(obj.modified, pg), tab_page)
        self.texstack.set_visible_child_name("view")
        self.tab_view.set_selected_page(tab_page)
        return tab_page


    def on_compiled(self, sender, success):
        self.btn_stack.set_visible_child_name("compile")
        if success:
            toast = Adw.Toast.new("Compile succeeded")
        else:
            toast = Adw.Toast.new("Compile failed")
            buf = self.sourceview.get_buffer()
            if buf.errors:
                it = buf.errors[0]
                self.sourceview.scroll_to_iter(it, 0.3, False, 0, 0)
                buf.place_cursor(it)
        toast.set_timeout(1)
        self.toast_overlay.add_toast(toast)

    def open_pdf(self,sender,path):
        self.pdfview.open_file(path)
        self.activate_action("win.synctex-fwd", None)


    def open_success_cb(self, sender, path):
        self.title.set_saved(True)
        subtitle,title = os.path.split(path)
        self.title.set_title_string(title)
        self.title.set_subtitle_string(subtitle)
        self.pdfview.open_file(os.path.splitext(path)[0] + '.pdf')


    def on_open_action(self, widget, _):

        dialog = TexFileChooser("open", self)
        dialog.connect("finished", self.on_open_response)
        dialog.run()

    def on_open_response(self, sender, file):
        pg = self.tab_view.get_selected_page() or self.create_new_tab()
        src = pg.get_child()
        if src.modified or src.title != "New Document":
            pg = self.create_new_tab()
            src = pg.get_child()
        src.load_file(file)


    def on_save_action(self, widget, _):

        if self.docmanager.file is not None:
            self.docmanager.save_file()
        else:
            dialog = TexFileChooser("save", self)
            dialog.connect("finished", lambda _, f: self.docmanager.save_file(f))
            dialog.show()

    def on_close_tab(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            self.close()
            return
        self.tab_view.close_page(pg)
        if self.tab_view.get_n_pages() == 0:
            self.texstack.set_visible_child_name("empty")

    def on_compile_action(self, widget, _):
        self.docmanager.to_compile = True
        self.activate_action("win.save")
        self.btn_stack.set_visible_child_name("cancel")

    def on_cancel_action(self, widget, _):
        self.documentmanager.cancel()

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


class TexFileChooser(GObject.GObject):

    __gsignals__ = {
        'finished': (GObject.SIGNAL_RUN_FIRST, None, (GtkSource.File,))
    }

    def __init__(self, action, parent):
        super().__init__()
        if action == "open":
            flag = Gtk.FileChooserAction.OPEN
            text = "Open file"
        elif action == "save":
            flag = Gtk.FileChooserAction.SAVE
            text = "Save file"

        dialog = Gtk.FileChooserNative.new(text, parent, flag, None, None)

        filter_tex = Gtk.FileFilter()
        filter_tex.set_name("Latex")
        filter_tex.add_mime_type("text/x-tex")
        dialog.add_filter(filter_tex)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)
        dialog.connect("response", self.dialog_response)
        self.dialog = dialog # to keep dialog alive until response is called

    def dialog_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = GtkSource.File.new()
            file.set_location(dialog.get_file())
            self.emit("finished", file)

    def run(self):
        self.dialog.show()

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
        self.set_saved(self.saved)

    def set_subtitle_string(self,s):
        self.subtitle_string = s
        self.subtitle.set_markup("<small>" + s + "</small>")

    def set_saved(self,b):
        self.saved = b
        if self.saved:
            self.title.set_markup("<b>" + self.title_string + "</b>")
        else:
            self.title.set_markup("<i><b>" + self.title_string + "*" + "</b></i>")

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

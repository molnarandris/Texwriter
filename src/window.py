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
    subtitle      = Gtk.Template.Child()
    is_modified   = Gtk.Template.Child()
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

        self.tab_view.connect("notify::selected-page", lambda obj, _: self.selected_tab_changed(obj, obj.get_selected_page()))
        self.title_binding = None

    def selected_tab_changed(self, tab_view, pg):
        src = pg.get_child()
        if self.title_binding:
            self.title_binding.unbind()
        flag = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        src.bind_property("title", self.title, "label", flag)
        src.bind_property("modified", self.is_modified, "visible", flag)

    def set_pg_icon(self, b, pg):
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
        src.connect("notify::modified", lambda obj, _ : self.set_pg_icon(obj.modified, tab_page))
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

    def on_open_action(self, widget, _):
        pg = self.tab_view.get_selected_page() or self.create_new_tab()
        src = pg.get_child()
        if src.modified or src.title != "New Document":
            pg = self.create_new_tab()
            src = pg.get_child()
        src.open()


    def on_save_action(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            return
        src = pg.get_child()
        src.save()

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

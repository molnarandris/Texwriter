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
from .utilities import ProcessRunner
from .documentmanager import  DocumentManager
from .tabpage import TabPage

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    btn_stack     = Gtk.Template.Child()
    toast_overlay = Gtk.Template.Child()
    main_stack    = Gtk.Template.Child()
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
        self.main_stack.set_visible_child_name("empty")

        self.tab_view.connect("notify::selected-page", lambda obj, _: self.selected_tab_changed(obj, obj.get_selected_page()))
        self.tab_view.connect("notify::n-pages", lambda obj,_ : self.on_n_tab_change(obj,obj.get_n_pages()))

        self.btn_stack_handler_id = None
        self.old_tab_page = None

        self.tab_view.connect("indicator-activated", self.on_indicator_activated)


    def on_indicator_activated(self, view, pg):
        pg.get_child().compile()

    def on_n_tab_change(self,tab_view, n):
        ''' Called when the number of tabs in the window change.
            If there is no more tabs present, sets empty view, otherwise
            sets the normal view.
        '''
        if n == 0:
            self.main_stack.set_visible_child_name("empty")
        else:
            self.main_stack.set_visible_child_name("non-empty")

    def selected_tab_changed(self, tab_view, pg):
        ''' Called when the selected tab is changed. We need to set the compile
            button to represent the state of the given tab page.
        '''
        # we need to update the compile button according to busyness of compiler
        if pg is None:
            return
        tab_page = pg.get_child()
        if self.old_tab_page and self.btn_stack_handler_id:
            self.old_tab_page.disconnect(self.btn_stack_handler_id)

        self.btn_stack_handler_id = tab_page.connect("notify::busy", lambda obj,_: self.btn_stack.set_visible_child_name("cancel") if obj.get_property("busy") else self.btn_stack.set_visible_child_name("compile"))
        self.old_tab_page = tab_page

    def set_pg_icon(self, b, pg):
        ''' Sets the icon of a given tab page
        '''
        if b:
            icon = Gio.ThemedIcon.new("document-modified-symbolic")
            pg.set_icon(icon)
        else:
            pg.set_icon(None)

    def set_pg_indicator_icon(self, busy, pg):
        if busy:
            icon = Gio.Icon.new_for_string("media-playback-stop-symbolic")
        else:
            icon = Gio.Icon.new_for_string("media-playback-start-symbolic")
        pg.set_indicator_icon(icon)

    def create_new_tab(self):
        pg = TabPage()
        tab_page = self.tab_view.append(pg)
        tab_page.set_indicator_icon(Gio.Icon.new_for_string("media-playback-start-symbolic"))
        tab_page.set_indicator_activatable(True)
        self.tab_view.set_selected_page(tab_page)
        flags = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        pg.sourceview.bind_property("title", tab_page, "title", flags)
        pg.sourceview.connect("notify::modified", lambda *_: self.set_pg_icon(pg.sourceview.modified, tab_page))
        pg.connect("notify::busy", lambda *_: self.set_pg_indicator_icon(pg.busy, tab_page))
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
        dialog = Gtk.FileChooserNative.new(
                    "Open File",
                    self.get_root(),
                    Gtk.FileChooserAction.OPEN,
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

        dialog.connect("response", self.on_open_response)
        dialog.set_modal(True)
        dialog.show()
        self.open_dialog = dialog

    def on_open_response(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            file = GtkSource.File.new()
            file.set_location(dialog.get_file())
            pg = self.tab_view.get_selected_page() or self.create_new_tab()
            src = pg.get_child().sourceview
            if src.modified or src.title != "New Document":
                pg = self.create_new_tab()
                src = pg.get_child().sourceview
            src.load_file(file)
        self.open_dialog = None


    def on_save_action(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            return
        src = pg.get_child().sourceview
        src.save()

    def on_close_tab(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            self.close()
            return
        self.tab_view.close_page(pg)

    def on_compile_action(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            return
        tab_page = pg.get_child()
        tab_page.compile()
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

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
from .editor_page import EditorPage
from .viewer_page import ViewerPage
from .texfile import TexFile

@Gtk.Template(resource_path='/com/github/molnarandris/texwriter/window.ui')
class TexwriterWindow(Adw.ApplicationWindow):
    __gtype_name__ = 'TexwriterWindow'

    btn_stack      = Gtk.Template.Child()
    toast_overlay  = Gtk.Template.Child()
    main_stack     = Gtk.Template.Child()
    tab_view       = Gtk.Template.Child()
    paned          = Gtk.Template.Child()
    pdf_stack      = Gtk.Template.Child()
    pdf_log_switch = Gtk.Template.Child()

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

        # This doesn't work from the ui file:
        self.paned.set_resize_start_child(True)
        self.paned.set_resize_end_child(True)

        actions = [
            ('open', self.on_open_action, ['<primary>o']),
            ('close', self.on_close_tab, ['<primary>w']),
            ('save', self.on_save_action, ['<primary>s']),
            ('compile', self.on_compile_action, ['F5']),
            ('synctex-fwd', self.on_synctex_action, ['F7']),
            ('cancel', self.on_cancel_action, []),
            ('new-tab', lambda *_: self.create_new_tab(), []),
        ]

        for a in actions: self.create_action(*a)
        self.main_stack.set_visible_child_name("empty")

        self.tab_view.connect("notify::selected-page", lambda obj, _: self.selected_tab_changed(obj, obj.get_selected_page()))
        self.tab_view.connect("notify::n-pages", lambda obj,_ : self.on_n_tab_change(obj,obj.get_n_pages()))
        self.pdf_stack.connect("notify::visible-child", lambda obj, _: self.viewer_tab_changed())

        self.btn_stack_handler_id = None
        self.old_viewer_page = None
        self.stack_switch_binding = None

        # Save opened files
        self.connect("close-request", self.on_close)

################################################################################
# Tab management

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
        editor_page = pg.get_child()
        if editor_page.file is None:
            self.pdf_stack.set_visible_child_name("empty")
            return
        path = editor_page.file.get_pdf_path()
        if path is None:
            self.pdf_stack.set_visible_child_name("empty")
            return
        viewer_page = self.pdf_stack.get_child_by_name(path)
        self.pdf_stack.set_visible_child(viewer_page)
        self.btn_stack.set_visible(True)

    def viewer_tab_changed(self):
        if self.old_viewer_page and self.btn_stack_handler_id:
            self.old_viewer_page.disconnect(self.btn_stack_handler_id)
        if self.stack_switch_binding:
            self.stack_switch_binding.unbind()
        viewer_page = self.pdf_stack.get_visible_child()
        if self.pdf_stack.get_visible_child_name() == "empty":
            self.btn_stack.set_visible(False)
            self.pdf_log_switch.set_visible(False)
            return
        self.pdf_log_switch.set_stack(viewer_page.main_stack)
        self.btn_stack_handler_id = viewer_page.connect("notify::busy", lambda obj,_: self.btn_stack.set_visible_child_name("cancel") if obj.get_property("busy") else self.btn_stack.set_visible_child_name("compile"))
        flags = GObject.BindingFlags.INVERT_BOOLEAN | GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.DEFAULT
        self.stack_switch_binding_id = viewer_page.bind_property("has_error", self.pdf_log_switch, "visible", flags)

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
        src = EditorPage()
        tab_page = self.tab_view.append(src)
        self.tab_view.set_selected_page(tab_page)
        flags = GObject.BindingFlags.DEFAULT | GObject.BindingFlags.SYNC_CREATE
        src.bind_property("title", tab_page, "title", flags)
        src.connect("notify::modified", lambda *_: self.set_pg_icon(src.modified, tab_page))
        self.pdf_stack.set_visible_child_name("empty")
        return tab_page

    def on_close_tab(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            self.close()
            return
        self.tab_view.close_page(pg)

    def get_tab_for_path(self, path):
        for pg in self.tab_view.get_pages():
            if pg.get_child().file and path == pg.get_child().file.get_tex_path():
                return pg
        return None

    def goto_tex(self, path, line, context, offset):
        pg = self.get_tab_for_path(path)
        if pg is None:
            pg = self.create_new_tab()
            editor_page = pg.get_child()
            editor_page.load(path, lambda: self.goto_tex(path, line, context, offset))
        else:
            editor_page = pg.get_child()
        self.tab_view.set_selected_page(pg)
        editor_page.goto(line,context,offset)




    ############################################################################
    # File opening

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
        self.open_dialog = None
        if response != Gtk.ResponseType.ACCEPT:
            return
        file = Gio.File.new_for_path()
        self.open_file(file)

    def open_file(self, file):
        path = file.get_path()
        tab_page = self.get_tab_for_path(path)
        if tab_page:
            self.tab_view.set_selected_page(tab_page)
            return
        tab_page = self.tab_view.get_selected_page() or self.create_new_tab()
        editor_page = tab_page.get_child()
        if editor_page.modified or editor_page.title != "New Document":
            tab_page = self.create_new_tab()
            editor_page = tab_page.get_child()
        editor_page.load_file(file, self.load_tex_response)

    def load_tex_response(self,success, file):
        path = file.get_pdf_path()
        if path is None:
            self.pdf_stack.set_visible_child_name("empty")
            return
        viewer_page = self.pdf_stack.get_child_by_name(path)
        if viewer_page is None:
            viewer_page = ViewerPage()
            viewer_page.set_file(file)
            viewer_page.load_pdf()
            viewer_page.load_log()
            self.pdf_stack.add_named(viewer_page, path)
        self.pdf_stack.set_visible_child(viewer_page)
        self.btn_stack.set_visible(True)
        self.pdf_log_switch.set_stack(self.pdf_stack.get_visible_child().main_stack)
        self.pdf_log_switch.set_visible(True)

    ############################################################################
    # Compilation

    def on_compile_action(self, widget, _):
        self.btn_stack.set_visible_child_name("cancel")
        self.compile()


    def compile(self, save = True):
        tab_page = self.tab_view.get_selected_page()
        if tab_page is None:
            return
        editor_page = tab_page.get_child()
        file = editor_page.file
        if file is None:
            return
        path = editor_page.file.get_pdf_path()
        viewer_page = self.pdf_stack.get_child_by_name(path)
        if viewer_page:
            viewer_page.set_property("busy", True)
        if save and editor_page.modified:
            editor_page.save(lambda: self.compile(False))
            return  # we have to wait for the saving to finish
        path = file.get_root_path()
        directory = file.get_dir()
        cmd = ['flatpak-spawn', '--host', 'latexmk', '-synctex=1', '-interaction=nonstopmode',
               '-pdf', "-g", "--output-directory="+ directory, path]
        flags = Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE
        proc = Gio.Subprocess.new(cmd, flags)
        proc.wait_async(None, self.on_compile_finished, tab_page)

    def on_compile_finished(self, proc, result, tab_page):
        try:
            proc.wait_finish(result)
        except:
            print("can't run latexmk")
            return

        editor_page = tab_page.get_child()
        file = editor_page.file
        path = file.get_pdf_path()
        viewer_page = self.pdf_stack.get_child_by_name(path)
        if viewer_page is None:
            viewer_page = ViewerPage()
            viewer_page.set_file(file)
            self.pdf_stack.add_named(viewer_page, path)
        viewer_page.set_property("busy", False)
        if not proc.get_successful():
            toast = Adw.Toast.new("Compile failed")
        else:
            toast = Adw.Toast.new("Compile succeeded")
            viewer_page.load_pdf()
            self.synctex_fwd(editor_page)
        path = tab_page.get_child().file.get_log_path()
        viewer_page.load_log()
        toast.set_timeout(1)
        self.toast_overlay.add_toast(toast)


    ############################################################################
    # Synctex

    def on_synctex_action(self, sender, _):
        tab_page = self.tab_view.get_selected_page()
        if tab_page is None:
            return
        editor_page = tab_page.get_child()
        self.synctex_fwd(editor_page)

    def synctex_fwd(self, editor_page):
        file = editor_page.file
        if file is None:
            return
        viewer_page = self.pdf_stack.get_child_by_name(file.get_pdf_path())
        editor_page.synctex_fwd(lambda s: self.synctex_fwd_finish(viewer_page, s))

    def synctex_fwd_finish(self, viewer_page, sync):
        viewer_page.pdfviewer.synctex_fwd(sync)
        viewer_page.main_stack.set_visible_child_name("pdfview")

    ############################################################################
    # Saving:
    def on_save_action(self, widget, _):
        pg = self.tab_view.get_selected_page()
        if pg is None:
            return
        editor_page = pg.get_child()
        editor_page.save()

    ############################################################################

    def on_close(self, win):
        files = []
        for tab_page in self.tab_view.get_pages():
            editor_page = tab_page.get_child()
            path = editor_page.get_tex_path()
            if path:
                files.append(path)
        # Save the files
        settings = Gio.Settings.new("com.github.molnarandris.texwriter")
        settings.set_strv("opened-files", files)

    def restore_session(self):
        settings = Gio.Settings.new("com.github.molnarandris.texwriter")
        for path in settings.get_strv("opened-files"):
            file = Gio.File.new_for_path(path)
            self.open_file(file)


    ############################################################################
    def on_cancel_action(self, widget, _):
        pass


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

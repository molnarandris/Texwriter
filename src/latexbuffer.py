from gi.repository import Gtk, GtkSource


class LatexBuffer(GtkSource.Buffer):

    def __init__(self):
        super().__init__()

        manager = GtkSource.LanguageManager()
        language = manager.get_language("latex")
        self.set_language(language)

        # Tags
        self.create_tag("Error", background ="#ff6666")
        self.create_tag("Warning", background ="#fae0a0")

        # List of text iters to the errors and warnings
        self.errors   = []
        self.warnings = []


    def clear_tags(self):
        bounds = self.get_bounds()
        self.remove_tag_by_name("Error", *bounds)
        self.remove_tag_by_name("Warning", *bounds)
        self.errors   = []
        self.warnings = []

    def highlight(self,tagname, line, text):
        begin_it = self.get_iter_at_line_offset(line, 0)[1]
        limit_it = self.get_iter_at_line_offset(line+1, 0)[1]
        result = begin_it.forward_search(text, Gtk.TextSearchFlags.TEXT_ONLY, limit_it)
        if result:
            self.apply_tag_by_name(tagname, *result)
            if tagname == "Error":
                self.errors.append(result[1])
            elif tagname == "Warning":
                self.warnings.append(result[1])
        print("Error found, ", tagname, self.errors)


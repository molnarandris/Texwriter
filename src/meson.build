pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'texwriter')
gnome = import('gnome')

# Don't forget to add the .ui to the gresource.xml!
blueprints = custom_target('blueprints',
  input: files(
    'window.blp',
    'pdfviewer.blp',
    'editor_page.blp',
    'viewer_page.blp',
  ),
  output: '.',
  command: [find_program('blueprint-compiler'), 'batch-compile', '@OUTDIR@', '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)




gnome.compile_resources('texwriter',
  'texwriter.gresource.xml',
  gresource_bundle: true,
  dependencies: blueprints,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'texwriter.in',
  output: 'texwriter',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

texwriter_sources = [
  '__init__.py',
  'main.py',
  'window.py',
  'pdfviewer.py',
  'latexbuffer.py',
  'editor_page.py',
  'texfile.py',
  'logprocessor.py',
  'viewer_page.py',
  'editor_page.py',
  'autocomplete.py',
]

install_data(texwriter_sources, install_dir: moduledir)

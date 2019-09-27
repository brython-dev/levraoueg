from browser import ajax, bind, confirm, document, window, alert, prompt, html
from browser import console
from browser.widgets.dialog import Dialog

import re

document["wait"].remove()
document["container"].style.visibility = "visible"
document["legend"].style.visibility = "visible"

import tb

from console import Console

translations = {
    "fr":{
        "close": "Fermer",
        "confirm_delete": "Voulez-vous supprimer le fichier\n{} ?",
        "file_changed": "Le fichier {} a changé.\nEnregistrer ?",
        "file_deleted": "Fichier supprimé",
        "new_script": "Nouveau script",
        "open": "Ouvrir",
        "redo": "Refaire",
        "save": "Enregistrer",
        "undo": "Défaire",
        "run_source": "Exécuter",
        "legend_text": """Editeur de code Python. Utilise
                <a href="https://brython.info" target="_blank">Brython</a> et
                <a href="https://ace.c9.io/">Ace</a>""",
        "trash": "Supprimer"
    }
}

language = document.query.getfirst("lang") # query string
if language is None:
    language = window.navigator.language # browser setting
    if language is not None:
        language = language[:2]

# Translate
if language in translations:
    for elt_id, translation in translations[language].items():
        if elt_id in document:
            document[elt_id].attrs["title"] = translation

# If there is an argument "file" in the query string, try to load a file
# of the same name in this HTML page's directory
load_file = document.query.getfirst("file")
if load_file:
    # try to load the file
    req = ajax.get(load_file,
        oncomplete=lambda evt: load3(evt.text, load_file))

# Set height of container to 80% of screen
height = document.documentElement.clientHeight
document['container'].style.height = f'{int(height * 0.8)}px'

# Set position of legend text
document['legend'].style.top = f'{int(height * 0.9)}px'

filezone = document["filezone"]
filebrowser = document["file-browser"]

open_files = {} # Maps file name to their content

editor = None

# Create a Python code editor with Ace
def create_editor():
    global editor
    document["editor"].style.backgroundColor = "#fff"
    editor = window.ace.edit("editor")
    editor.setTheme("ace/theme/github")
    editor.session.setMode("ace/mode/python")
    editor.focus()
    editor.on("change", editor_changed)
    return editor

def editor_changed(*args):
    """Called when the editor content changes."""
    current = document.select(".current")
    if current:
        filename = current[0].text.rstrip("*")
        if open_files[filename]["content"] != editor.getValue():
            if not current[0].text.endswith("*"):
                current[0].text += "*"
        elif current[0].text.endswith("*"):
            current[0].text = current[0].text.rstrip("*")

def _(id, default):
    """Translation."""
    if language and language in translations and \
            id in translations[language]:
        return translations[language][id]
    return default

# indexedDB
IDB = window.indexedDB
request = IDB.open("brython_scripts")

@bind(request, "upgradeneeded")
def create_db(evt):
    # The database did not previously exist, so create object store.
    db = evt.target.result
    store = db.createObjectStore("scripts", {"keyPath": "name"})

@bind(request, "success")
def check_db(evt):
    db = request.result
    tx = db.transaction("scripts", "readonly")
    store = tx.objectStore("scripts")
    req = store.count('truc.py*')

    @bind(req, "success")
    def check(evt):
        if evt.target.result:
            tx = db.transaction("scripts", "readwrite")
            store = tx.objectStore("scripts")
            req = store.delete('truc.py*')

            @bind(req, "success")
            def deleted(evt):
                print("delete !")

@bind("#new_script", "click")
def new_script(evt):
    """Create new script. Give it the name moduleX.py where X is the first
    number available."""
    db = request.result
    tx = db.transaction("scripts", "readonly")
    store = tx.objectStore("scripts")
    cursor = store.openCursor()

    nums = []

    def get_scripts(evt):
        res = evt.target.result
        if res:
            name = res.value.name
            mo = re.match("^module(\d+).py$", name)
            if mo:
                nums.append(int(mo.groups()[0]))
            getattr(res, "continue")()
        else:
            if not nums:
                num = 1
            else:
                num = max(nums) + 1
            create_editor()
            editor.setValue("")
            filename = f"module{num}.py"
            open_files[filename] = {"content": "", "cursor": [0, 0]}
            update_filebrowser(filename)

    cursor.bind('success', get_scripts)

@bind("#run_source", "click")
def run(evt):
    """Run the script and start the interactive session in the console with
    the script namespace."""
    ns = {}
    output.clear()
    try:
        exec(editor.getValue(), ns)
        # Set console namespace
        output.namespace = ns
    except:
        tb.print_exc(file=output)
    output.prompt()

def display(evt):
    """Called on click on a filename in the file browser (left column)."""
    file_name = evt.target.text
    # Store current file
    current = document.select_one(".current")
    if current.text == file_name:
        rename(current)
        return
    position = editor.getCursorPosition()
    open_files[current.text] = {
        "content": editor.getValue(),
        "cursor": [position.row, position.column]
    }

    # Put highlight on new file
    current.classList.remove("current")
    evt.target.classList.add("current")

    # Load selected file
    new_file = open_files[file_name]
    editor.setValue(new_file["content"])
    editor.moveCursorTo(*new_file["cursor"], False)
    editor.scrollToLine(new_file["cursor"][0], True)
    editor.clearSelection()
    editor.focus()

def rename2(evt, old_name):
    new_name = evt.target.value
    if new_name == old_name:
        update_filebrowser(old_name)
        return

    # Search if new name already exists
    db = request.result
    tx = db.transaction("scripts", "readonly")
    store = tx.objectStore("scripts")
    req = store.count(new_name)

    @bind(req, "success")
    def exists(evt):
        if evt.target.result:
            # A script of the same name already exists
            replace = confirm("A script called " + new_name +
                " already exists. Overwrite ?")
            if replace:
                # Replace existing script
                tx = db.transaction("scripts", "readwrite")
                store = tx.objectStore("scripts")
                data = {"name": new_name, "content": editor.getValue()}
                req = store.put(data)

                @bind(req, "success")
                def replaced(evt):
                    # Now delete script with old name
                    req = store.delete(old_name)

                    @bind(req, "success")
                    def removed(evt):
                        del open_files[old_name]
                        if not new_name in open_files:
                            open_files[new_name] = {
                                "content": editor.getValue(),
                                "cursor":[0, 0]
                            }
                        update_filebrowser(new_name)
        else:
            # New script
            tx = db.transaction("scripts", "readwrite")
            store = tx.objectStore("scripts")
            data = {"name": new_name, "content": editor.getValue()}
            req = store.put(data)

            @bind(req, "success")
            def created(evt):
                del open_files[old_name]
                open_files[new_name] = {"content": "", "cursor": [0, 0]}
                update_filebrowser(new_name)


def keyup_rename(evt, filename):
    """Handle two special keys, Escape and Enter."""
    if evt.keyCode == 27: # Escape key: cancel
        evt.target.parent.remove()
        update_filebrowser(filename)
        evt.preventDefault()
        evt.stopPropagation()
    elif evt.keyCode == 13: # Enter key: same as blur
        rename2(evt, filename)
        evt.preventDefault()
        evt.stopPropagation()

def rename(current):
    """Rename current file."""
    current.unbind("click", display)
    filename = current.text.rstrip("*")
    current.html = f'<input value="{filename}">'
    entry = current.children[0]
    pos = filename.find(".")
    entry.setSelectionRange(pos, pos)
    entry.bind("blur", lambda evt: rename2(evt, filename))
    entry.bind("keyup", lambda evt: keyup_rename(evt, filename))
    entry.focus()

def update_filebrowser(current=None):
    """Update the file browser with all the open files, highlight current
    script."""
    files = list(open_files)
    files.sort()
    filebrowser.clear()
    for f in files:
        line = html.DIV(f, Class="pyfile")
        if f == current:
            line.classList.add("current")
        line.bind("click", display)
        filebrowser <= line

def load3(content, filename):
    """Load the filename's content in the editor, update data."""
    open_files[filename] = {"content": content, "cursor": [0, 0]}
    update_filebrowser(filename)

    create_editor()
    editor.setValue(content)
    editor.moveCursorTo(0, 0, False)
    editor.focus()

def open_script(evt):
    """Open one of the scripts shown in the dialog window generated by
    load().
    """
    current = evt.target.text
    db = request.result
    tx = db.transaction("scripts", "readonly")
    store = tx.objectStore("scripts")
    req = store.get(current)

    def success(evt):
        if not hasattr(req, "result"):
            print("not found")
        else:
            load3(req.result.content, current)

    dialog_window = evt.target.parent.parent
    dialog_window.remove()

    req.bind("success", success)

@bind("#open", "click")
def vfs_open(evt):
    """Search all file names in the indexedDB database, open a dialog window
    to select a file to open."""
    db = request.result
    tx = db.transaction("scripts", "readonly")
    store = tx.objectStore("scripts")
    cursor = store.openCursor()

    dialog_window = Dialog("Open file...",
                           top=filebrowser.abs_top,
                           left=filebrowser.abs_left)

    scripts = []
    script_style = {
        "cursor": "default"
    }
    def get_scripts(evt):
        res = evt.target.result
        if res:
            scripts.append(res.value.name)
            getattr(res, "continue")()
        else:
            scripts.sort()
            for script in scripts:
                script_elt = html.SPAN(script, style=script_style)
                dialog_window.panel <= script_elt + html.BR()
                script_elt.bind("click", open_script)

    cursor.bind('success', get_scripts)

def _remove(filename):
    """Remove an open file. Used by close() and trash()."""
    del open_files[filename]
    if open_files:
        files = list(open_files)
        filename = files[-1]
        update_filebrowser(filename)
        editor.setValue(open_files[filename]["content"])
    else:
        filebrowser.clear()
        document["editor"].clear()
        document["editor"].style.backgroundColor = "#aaa"
        editor.destroy()

@bind("#close", "click")
def close(evt):
    """Close an open file."""
    current = filebrowser.select_one(".current")
    if current is None:
        return
    filename = current.text
    if filename.endswith("*"):
        msg = _("file_changed", "File {} changed; save it ?")
        resp = confirm(msg.format(filename.rstrip("*")))
        if resp:
            save(evt)
        filename = filename[:-1]
    _remove(filename)

@bind("#redo", "click")
def redo(evt):
    manager = editor.session.getUndoManager()
    if manager.hasRedo():
        editor.redo()
        editor.clearSelection()
        editor.focus()

@bind("#undo", "click")
def undo(evt):
    if editor.session.getUndoManager().hasUndo():
        editor.undo()

@bind("#save", "click")
def save(evt):
    """Save the current script in the database."""
    current = filebrowser.select_one(".current")
    if current is None:
        return
    name = current.text
    if not name:
        return
    name = name.rstrip("*")
    db = request.result
    tx = db.transaction("scripts", "readwrite")
    store = tx.objectStore("scripts")
    cursor = store.openCursor()
    data = {"name": name, "content": editor.getValue()}
    store.put(data)

    # When record is added, show message
    def ok(evt):
        current.text = name
        alert("saved")

    cursor.bind('success', ok)

@bind("#trash", "click")
def trash(evt):
    """Delete a file."""
    current = filebrowser.select_one(".current")
    if current is None:
        return
    name = current.text
    if not name:
        return
    name = name.rstrip("*")
    msg = _("confirm_delete", "Do you want to delete\nfile {} ?")
    resp = confirm(msg.format(name))
    if not resp:
        return
    db = request.result
    tx = db.transaction("scripts", "readwrite")
    store = tx.objectStore("scripts")
    cursor = store.openCursor()
    store.delete(name)

    def ok(evt):
        alert(_("file_deleted", "File deleted"))
        _remove(name)

    cursor.bind("success", ok)

# Create the interactive Python console
output = Console(document["console"])
output.prompt()
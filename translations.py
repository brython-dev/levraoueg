from browser import document, window

translations = {
    "fr":{
        "close": "Fermer",
        "export": "Exporter vers un fichier local", 
        "import": "Importer depuis un fichier local",
        "new_script": "Nouveau script",
        "open": "Ouvrir",
        "redo": "Refaire",
        "save": "Enregistrer",
        "undo": "Défaire",
        "run_source": "Exécuter",
        "legend_text": """Editeur de code Python. Utilise
                <a href="https://brython.info" target="_blank">Brython</a> et
                <a href="https://ace.c9.io/">Ace</a>""",
        "trash": "Supprimer",
        # dialog boxes
        "Delete file": "Suppression de fichier",
        "Do you want to delete\nfile {} ?":
                "Voulez-vous supprimer\nle fichier {} ?",
        "file_changed": "Le fichier {} a changé.\nEnregistrer ?",
        "file_deleted": "Fichier supprimé",
        "File {} deleted": "Fichier {} supprimé",
    }
}

language = document.query.getfirst("lang") # query string
if language is None:
    language = window.navigator.language # browser setting
    if language is not None:
        language = language[:2]

# Translate elements in the page whose id is in translations
if language in translations:
    for elt_id, translation in translations[language].items():
        if elt_id in document:
            document[elt_id].attrs["title"] = translation

def _(id, default=None):
    """Translation."""
    if language and language in translations and \
            id in translations[language]:
        return translations[language][id]
    return default or id
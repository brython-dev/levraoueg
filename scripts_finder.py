import sys
from browser import console

class ScriptsFinder:
    """Meta path finder, uses dictionary "scripts"."""

    scripts = {}

    @classmethod
    def find_spec(cls, name, path=None):
        fullname = name + ".py"
        if fullname in ScriptsFinder.scripts:
            spec = ModuleSpec(name, ScriptsFinder)
            spec.cached = False
            spec.has_location = True
            spec.loader_state = {
                "content": ScriptsFinder.scripts[fullname],
                "path": fullname,
                "is_package": False
            }
            spec.origin = fullname
            spec.parent = fullname
            spec.submodule_search_locations = None
            return spec

    @classmethod
    def create_module(cls, spec):
        pass

    @classmethod
    def exec_module(cls, module):
        spec = module.__spec__
        sys.modules[spec.name] = module
        ns = {}
        # execute source code of Python module
        exec(spec.loader_state["content"], ns)
        for key, value in ns.items():
            setattr(module, key, value)

class ModuleSpec:

    def __init__(self, name, loader):
        self.name = name
        self.loader = loader

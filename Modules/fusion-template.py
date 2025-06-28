import builtins, inspect, json, os, traceback
from enum import Enum, auto
from functools import wraps
from functools import _Wrapped # type: ignore
from importlib.machinery import SourceFileLoader, SOURCE_SUFFIXES
from pathlib import Path
from typing import (
    Any, Callable, Protocol, Sequence, Iterable, runtime_checkable
)
from types import FrameType, ModuleType

import adsk.core


# Common static variables.
self_file = Path(__file__)        # Our current script's path.
addin_dir = Path(__file__).parent # Our add-in directory.
manifest_file = addin_dir / 'manifest.json'  # Our add-in's manifest.
with manifest_file.open() as f:
    manifest = json.load(f)       # Our add-in's manifest data.
addin_name = self_file.stem       # Our add-in's name.
debug = bool(manifest.get('editEnabled', False))  # Whether we're in debug mode.


# Our add-in's path prefix according to `inspect` (formatted for comparison).
current_frame = inspect.currentframe()
try:
    addin_prefix = (
        current_frame
            .f_code # type: ignore
            .co_filename
            [:-len(self_file.name)]
    )
finally:
    del current_frame


def _walk_stack(frame: FrameType|None, skip: int = 1) -> Iterable[FrameType]:
    """ Iterator that walks the stack beginning at the given frame. """
    if frame:
        for _ in range(skip):
            if not frame: return
            frame = frame.f_back
    while frame:
        yield frame
        frame = frame.f_back


# Various signatures for typing purposes
Action = Callable[[], None]
ImportCallable = Callable[
    [str, dict[str, Any]|None, dict[str, Any]|None, Sequence[str], int],
    ModuleType
]
WrappedImportCallable = _Wrapped[
    [str, dict[str, Any]|None, dict[str, Any]|None, Sequence[str], int],
    ModuleType,
    [str, dict[str, Any]|None, dict[str, Any]|None, Sequence[str], int],
    ModuleType
]


class ModuleKind(Enum):
    """
    Indicates whether a module is a package directory, a module file,
    or is not found.
    """
    PACKAGE_DIR = auto()
    MODULE_FILE = auto()
    NOT_FOUND = auto()


# Autodesk application instance.
# Automatically updates when invalidated.
_adsk_app: adsk.core.Application | None = None
def adsk_app() -> adsk.core.Application:
    global _adsk_app
    if not _adsk_app or not _adsk_app.isValid:
        _adsk_app = adsk.core.Application.get()
    assert _adsk_app.isValid
    return _adsk_app


# Logging functions.
def log(source: str, level: str, x: str, *args: Any) -> None:
    adsk_app().log(f"{addin_name} {source}: [{level}] {x.format(*args)}")

def log_trace_pkg(x: str, *args: Any) -> None:
    if debug:
        log("Package Loader", "TRACE", x, *args)

def log_error_pkg(x: str, *args: Any) -> None:
    log("Package Loader", "ERROR", x, *args)

def log_trace_addin(x: str, *args: Any) -> None:
    if debug:
        log("Addin Loader", "TRACE", x, *args)

def log_error_addin(x: str, *args: Any) -> None:
    log("Addin Loader", "ERROR", x, *args)


def create_import_wrapper(
    import_base: ImportCallable
) -> tuple[WrappedImportCallable, Action]:
    """
    Creates a package loader wrapper for the __import__ function.

    Returns:
        tuple[WrappedImportCallable, Action]:
            The wrapper and a function to disable it.
    """
    
    # A kill switch that can be used to disable the wrapper.
    # We need to be able to disable the wrapper if we lose control
    # of the __import__ function
    # (e.g. if another add-in patches over our patch).
    disabled = False

    # Names we can safely ignore.
    ignore: set[str] = set()

    # Modules we've already loaded.
    loaded_modules: dict[str, ModuleType] = {}

    @wraps(import_base)
    def import_wrapper(
        name: str,
        globals: dict[str, Any] | None = None,
        locals: dict[str, Any] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        """
        Monkey-patches `__import__` to locate our packages.

        While this kind of hack is generally not recommended (for good reasons),
        this actually appears to be the safest way to provide package isolation
        between Fusion add-ins.

        Defers to existing `__import__` if the package is not in our collection.

        Returns:
            ModuleType: The imported module.
        """
        try:
            if disabled:
                log_trace_pkg("Import ignored: wrapper disabled.")
                return import_base(name, globals, locals, fromlist, level)

            # self._log_trace_pkg("Checking import of {}", name)
            current_frame = inspect.currentframe()
            current_stack = _walk_stack(current_frame)
            
            try:
                # Quick exit for relative imports.
                if name.startswith("."):
                    log_trace_pkg("Relative import ignored: {}", name)
                    return import_base(name, globals, locals, fromlist, level)
                
                # Quick exit for ignored imports.
                if name in ignore:
                    log_trace_pkg("Import ignored: {}", name)
                    return import_base(name, globals, locals, fromlist, level)

                # Exit if we're entirely outside our add-in.
                if not any(
                    frame.f_code.co_filename.startswith(addin_prefix)
                    for frame in current_stack
                ):
                    log_trace_pkg("External import ignored: {}", name)
                    return import_base(name, globals, locals, fromlist, level)

                # Quick resolution if the module is already loaded.
                if name in loaded_modules:
                    log_trace_pkg("Found module in cache: {}", name)
                    return loaded_modules[name]

                path = addin_dir / "Packages" / os.path.sep.join(name.split("."))

                # Check for module files.
                for suffix in SOURCE_SUFFIXES:
                    file_path = path.with_suffix(suffix)
                    if file_path.is_file():
                        log_trace_pkg("Resolved {} -> {}", name, file_path)
                        loader = SourceFileLoader(name, str(file_path))
                        module = loader.load_module(name)
                        loaded_modules[name] = module
                        return module
                
                # Check for package directories.
                for suffix in SOURCE_SUFFIXES:
                    init_path = path / f"__init__{suffix}"
                    if init_path.is_file():
                        log_trace_pkg("Resolved {} -> {}", name, init_path)
                        loader = SourceFileLoader(name, str(init_path))
                        module = loader.load_module(name)
                        module.__path__ = [str(path.parent)]
                        module.__package__ = name
                        loaded_modules[name] = module
                        return module
                
                # Not found.
                log_trace_pkg("Unresolved: {}", name)
                ignore.add(name)
                return import_base(name, globals, locals, fromlist, level)
            
            finally:
                del current_frame

        except:
            # Handle errors gracefully.
            # We're in a monkey-patch: tread lightly.
            log_error_pkg(
                "Unexpected error checking module {}.\n{}",
                name, traceback.format_exc()
            )
            return import_base(name, globals, locals, fromlist, level)
        
    def disable():
        nonlocal disabled
        disabled = True
        
    return import_wrapper, disable


_current_patch: tuple[WrappedImportCallable, Action]|None = None


def monkey_patch() -> None:
    """ Monkey-patches the __import__ function with our package loader. """
    global _current_patch
    if _current_patch:
        log_trace_pkg("Cannot patch importer: already patched.")
        return
    log_trace_pkg("Patching importer.")
    import_base: ImportCallable = builtins.__import__
    _current_patch = create_import_wrapper(import_base)
    importer, _ = _current_patch
    builtins.__import__ = importer


def monkey_unpatch() -> None:
    """ Unpatches (or otherwise disables) our monkey-patch. """
    global _current_patch
    if not _current_patch:
        log_trace_pkg("Cannot unpatch importer: not patched.")
        return
    importer, kill_switch = _current_patch
    if importer.__wrapped__ != builtins.__import__:
        log_error_pkg(
            "Importer has been patched over. Relying solely on kill switch."
        )
        kill_switch()
        _current_patch = None
        return
    log_trace_pkg("Unpatching importer.")
    builtins.__import__ = importer.__wrapped__
    _current_patch = None


@runtime_checkable
class AddinPattern(Protocol):
    """ The expected protocol for our add-in. """
    def fusion_run(self) -> None: ...
    def fusion_stop(self) -> None: ...


_app: AddinPattern|None = None # Our add-in instance.


def run(context: Any):
    """ Fusion entrypoint. """
    global _app
    try:
        log_trace_addin("Starting add-in.")

        monkey_patch()

        from my_module import MyClass # type: ignore
        app: AddinPattern = MyClass() # type: ignore
        assert isinstance(app, AddinPattern)
        _app = app
        _app.fusion_run()
    
    except Exception :
        log_error_addin(f"Error starting add-in.\n{traceback.format_exc()}")


def stop(context: Any):
    """ Fusion stop signal. """
    global _app
    try:
        log_trace_addin("Stopping add-in.")
        
        if _app:
            _app.fusion_stop()
            log_trace_addin("Stopped add-in.")
        _app = None

    except:
        log_error_addin(f"Error stopping add-in.\n{traceback.format_exc()}")

    try:
        monkey_unpatch()
    except:
        log_error_pkg(f"Error unpatching.\n{traceback.format_exc()}")

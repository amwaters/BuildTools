import json, os, re, shutil
from pathlib import Path
from typing import Any, Iterable, Mapping
import zipfile

from subprocess_build import cmd


_fusion_python_globs = [
    ('/', '*/Users/*/AppData/Local/Autodesk/webdeploy/production/*/Python/python.exe' ),
    ('/mnt', '*/Users/*/AppData/Local/Autodesk/webdeploy/production/*/Python/python.exe' ),
]
def _get_python_interpreter() -> Path:
    """
    Gets Fusion's Python interpreter.

    If `suggested_path` is provided and exists, it is preferred.
    Otherwise, the first file matching the usual glob patterns is used.

    If no file is found, a ValueError is raised.
    """
    try:
        return next(iter(
            p
            for root, glob in _fusion_python_globs
            for p in Path(root).glob(glob)
            if p.exists() and p.is_file()
        ))
    except StopIteration as e:
        raise ValueError(
            "No Fusion Python interpreter found."
        ) from e


_re_py_version = re.compile(r'^\s*Python\s*([\d\.]+)\s*$')
def get_python_version() -> str:
    fpy_path = _get_python_interpreter()
    python_version = cmd([fpy_path, '--version']).out
    match = _re_py_version.match(python_version)
    if not match:
        raise ValueError(
            f"Failed to parse Python version from {python_version!r}"
        )
    return match.group(1)


_python_pin_pattern = re.compile(r'python ==[\d\.]+\n?|$')
def _pin_python_version(conda_prefix: Path) -> None:
    conda_pin = conda_prefix / 'conda-meta' / 'pinned'
    python_version = get_python_version()
    content = ""
    if conda_pin.exists():
        content = conda_pin.read_text()
    if content and content[-1] != '\n':
        content += '\n'
    content = _python_pin_pattern.sub(
        f"python =={python_version}\n",
        content,
        count = 1
    )
    os.makedirs(conda_pin.parent, exist_ok=True)
    conda_pin.write_text(content)


_fusion_defs_globs = [
    ('/', '*/Users/*/AppData/Roaming/Autodesk/Autodesk Fusion 360/API/Python/defs'),
    ('/mnt', '*/Users/*/AppData/Roaming/Autodesk/Autodesk Fusion 360/API/Python/defs'),
]
def _copy_stubs(project_root: Path) -> None:
    defs = next(iter(
        p
        for root, glob in _fusion_defs_globs
        for p in Path(root).glob(glob)
        if p.exists() and p.is_dir()
    ))
    dest = project_root / '.cache' / 'defs'
    os.makedirs(dest, exist_ok=True)
    shutil.copytree(defs, dest, dirs_exist_ok=True)


def dev_setup(project_root: Path) -> None:
    conda_prefix = Path(os.environ['CONDA_PREFIX'])
    _pin_python_version(conda_prefix)
    _copy_stubs(project_root)


def _build_manifest(
    build_dir: Path,
    name: str,
    version: str,
    debug: bool,
    metadata: Mapping[str, Any]
) -> None:
    manifest_path = build_dir / name / 'manifest.json'
    manifest = dict(
        autodeskProduct = "Fusion",
        type = "addin",
        id = "",
        author = str(metadata.get('author', "")),
        description = { '': str(metadata.get('description', "")) },
        version = version,
        runOnStartup = not debug,
        supportedOS = "windows|mac",
        editEnabled = debug,
        iconFilename = str(metadata.get('iconFilename', "AddInIcon.svg")),
    )
    os.makedirs(manifest_path.parent, exist_ok=True)
    with manifest_path.open('w') as f:
        json.dump(manifest, f, indent=2)


def _build_script(
    build_dir: Path,
    name: str,
    debug: bool,
    metadata: Mapping[str, Any]
) -> None:
    template = Path(__file__).parent.resolve() / 'fusion-template.py'
    script = build_dir / name / f'{name}.py'
    content = template.read_text()
    content = content.replace('my_module', metadata['module'])
    content = content.replace('MyClass', metadata['class'])
    os.makedirs(script.parent, exist_ok=True)
    script.write_text(content)


package_suffix_blacklist = (
    '__pycache__',
    '.dist-info',
    '.egg-info',
    '.pth',
)
def _build_packages(
    build_dir: Path,
    name: str,
    packages_dirs: Iterable[Path],
) -> None:
    target = build_dir / name / 'Packages'
    os.makedirs(target, exist_ok=True)
    for packages_dir in packages_dirs:
        for package in packages_dir.glob('*'):
            if package.name.endswith(package_suffix_blacklist):
                continue
            if package.is_dir():
                shutil.copytree(package, target / package.name, dirs_exist_ok=True)
            else:
                shutil.copy(package, target / package.name)


def build(
    project_root: Path,
    name: str,
    version: str,
    debug: bool,
    metadata: Mapping[str, Any],
    packages_dirs: Iterable[Path],
) -> None:
    build_dir = project_root / '.build'
    print("Building manifest.")
    _build_manifest(build_dir, name, version, debug, metadata)
    print("Building main add-in script.")
    _build_script(build_dir, name, debug, metadata)
    print("Collecting add-in packages.")
    _build_packages(build_dir, name, packages_dirs)


def publish(
    project_root: Path,
    name: str,
    version: str
):
    source = project_root / '.build' / name
    target = project_root / '.build' / f'{name}-{version}.zip'
    with zipfile.ZipFile(target, 'w') as zf:
        for file_path in source.rglob('*'):
            if file_path.is_file():
                arc_name = file_path.relative_to(source)
                zf.write(file_path, arc_name)

import venv
from pathlib import Path
from typing import Any

from subprocess_build import ArgLike, cmd, CmdResult


def _py(prefix: Path, *args: ArgLike, **sp_kwargs: Any) -> CmdResult:
    return cmd([ prefix / 'bin' / 'python', *args ], **sp_kwargs)

def _pip(prefix: Path, *args: ArgLike, **sp_kwargs: Any) -> CmdResult:
    return _py(prefix, '-m', 'pip', *args, **sp_kwargs)

def _package_type(arg: str|Path) -> tuple[str, ...]:
    if isinstance(arg, Path) and arg.is_dir():
        return ('-e', str(arg))
    if isinstance(arg, Path) and arg.is_file():
        return ('-r', str(arg))
    return (str(arg),)

def pip_install(
    prefix: Path,
    *args: str|Path,
    upgrade: bool = False,
    **sp_kwargs: Any
):
    arg_list = sum((_package_type(arg) for arg in args), ())
    if upgrade: arg_list = ('--upgrade',) + arg_list
    _pip(prefix, 'install', *arg_list, **sp_kwargs).check()

# def _pip_install(prefix: Path, *args: ArgLike, upgrade: bool = False, **sp_kwargs: Any) -> CmdResult:
#     arg_list = list(args)
#     if upgrade: arg_list.insert(0, '--upgrade')
#     return _pip(prefix, 'install', *arg_list, **sp_kwargs)

# def install_project(prefix: Path, project: Path, upgrade: bool = False):
#     _pip_install(prefix, '-e', str(project), upgrade=upgrade).check()

# def install_requirements(prefix: Path, requirements: Path, upgrade: bool = False):
#     _pip_install(prefix, '-r', str(requirements), upgrade=upgrade).check()

# def install_packages(prefix: Path, *packages: str, upgrade: bool = False):
#     _pip_install(prefix, *packages, upgrade=upgrade).check()

def freeze(prefix: Path) -> str:
    return _pip(prefix, 'freeze').out

def create_venv(prefix: Path, clear: bool = False):
    venv.create(
        str(prefix),
        with_pip = True,
        clear = clear
    )
    pip_install(prefix, 'pip', upgrade=True)
    pip_install(prefix, 'setuptools', 'wheel')

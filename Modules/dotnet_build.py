from pathlib import Path
from subprocess_build import cmd, CmdResult


def dotnet(repo: Path, *args: str) -> CmdResult:
    return cmd(['dotnet', *args], cwd=repo)

def dotnet_build(repo: Path, *args: str) -> CmdResult:
    return dotnet(repo, 'build', *args)

def dotnet_restore(repo: Path, *args: str) -> CmdResult:
    return dotnet(repo, 'restore', *args)

def dotnet_test(repo: Path, *args: str) -> CmdResult:
    return dotnet(repo, 'test', *args)

from pathlib import Path
from subprocess_build import cmd, CmdResult


def git(repo: Path, *args: str) -> CmdResult:
    return cmd(['git', *args], cwd=repo)

def git_hash(repo: Path, short: bool = True) -> str:
    args: list[str] = []
    if short: args.append('--short')
    return git(repo, 'rev-parse', *args, 'HEAD').out.strip()

def git_dirty(repo: Path) -> bool:
    return git(repo, 'status', '--porcelain').out.strip() != ''

def git_hash_dirty(repo: Path) -> str:
    result = git_hash(repo)
    if git_dirty(repo):
        result += '-dirty'
    return result

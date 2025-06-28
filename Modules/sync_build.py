import os, shutil, time
from math import floor
from pathlib import Path
from typing import Iterable


def sync(
    dirs: Iterable[tuple[Path, Path]],
    watch: bool = False,
    poll_interval_s: float = 3,
    suffix_blacklist: Iterable[str]|None = None
) -> None:
    """
    Synchronises the contents of source-target directory pairs (recursively).
    If `watch` is True, will poll for changes every `poll_interval_s` seconds
    until SIGINT.
    Does not delete files in the target directory that are not in the source
    directory.
    """
    suffix_blacklist = list(suffix_blacklist or ())
    if watch:
        print(
            f"Watching for changes in {sum(1 for _ in dirs)} directories "
            f"(poll {poll_interval_s:.0f}s)..."
        )
        print("  Press Ctrl+C to stop.")
        print()
    try:
        while True:
            n = 0
            for s, t in _ops(dirs, suffix_blacklist):
                if t.exists() and t.is_file():
                    t_stat = t.stat()
                    s_stat = s.stat()
                    if (
                        floor(t_stat.st_mtime) == floor(s_stat.st_mtime)
                        and t_stat.st_size == s_stat.st_size
                    ):
                        continue
                print(f"Copy: {s.name} ---> {t.name}")
                os.makedirs(t.parent, exist_ok=True)
                shutil.copy2(s, t)
                n += 1
            if not watch: 
                print(f"Synced {n} files.")
                return
            if n > 0:
                print(f"Synced {n} files.")
            time.sleep(poll_interval_s)
    except KeyboardInterrupt:
        if not watch: raise
        print("Stopped watching.")
        print()


def _ops(
    dirs: Iterable[tuple[Path, Path]],
    suffix_blacklist: Iterable[str]
) -> Iterable[tuple[Path, Path]]:
    for s_dir, t_dir in dirs:
        for s_file in s_dir.rglob('*'):
            relative_path = s_file.relative_to(s_dir)
            if (
                s_file.is_dir()
                or any(
                    p.endswith(suffix)
                    for p in relative_path.parts
                    for suffix in suffix_blacklist
                )
            ): continue
            t_file = t_dir / relative_path
            yield s_file, t_file

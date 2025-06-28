import subprocess
from pathlib import Path
from typing import Any


ArgLike = str|Path


class CmdResult:
    def __init__(self, result: subprocess.CompletedProcess[str]):
        self.result = result
    
    def check(self) -> None:
        if self.result.returncode != 0:
            print(f"Error running command (rc={self.result.returncode}):")
            print(self.result.args)
            if self.result.stdout:
                print(f"=== STDOUT ===")
                print(self.result.stdout)
            if self.result.stderr:
                print(f"=== STDERR ===")
                print(self.result.stderr)
            if self.result.stdout or self.result.stderr:
                print(f"==============")
            raise subprocess.CalledProcessError(
                self.result.returncode,
                self.result.args,
                self.result.stdout,
                self.result.stderr
            )
    
    @property
    def rc(self) -> int:
        return self.result.returncode

    @property
    def out(self) -> str:
        self.check()
        return self.result.stdout or ''


def _fmt_arg(x: ArgLike) -> str:
    if isinstance(x, Path):
        return str(x.resolve())
    return x


def cmd(
    cmd: list[ArgLike],
    **sp_kwargs: Any
) -> CmdResult:
    return CmdResult(
        subprocess.run(
            [ _fmt_arg(c) for c in cmd ],
            capture_output = True,
            text = True,
            **sp_kwargs
        )
    )

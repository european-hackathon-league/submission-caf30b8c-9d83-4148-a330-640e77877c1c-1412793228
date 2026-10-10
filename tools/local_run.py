"""Local run harness: load the public scouting run into this process and run starter-kit/agent.py on your machine.

Run it with the starter kit's Python (starter-kit/.venv), from any directory:

    python tools/local_run.py --check                       # what gets set, is the model proxy up; runs nothing
    python tools/local_run.py --headed --no-submit          # watch the browsers, stop before the bid form
    python tools/local_run.py --sites ID,ID --log run.log   # only those site agents, output also in run.log
    python tools/local_run.py --no-submit --dump case.json  # keep the case file the agents filled

`atira scout --challenge rfq --env` prints the run's variables as shell lines, the practice logins among them. They
are parsed in memory and put into os.environ, where the agent reads them (run.py `load_run`): never printed, never
written to disk, and read before --log starts. The model proxy is not started here: keep `atira models proxy` running
in another terminal. This file lives outside starter-kit so that it is never packaged.
"""
import argparse
import asyncio
import importlib
import inspect
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlsplit

STARTER_KIT = Path(__file__).resolve().parent.parent / "starter-kit"
SCOUT = ("scout", "--challenge", "rfq", "--env")
SCOUT_TIMEOUT = 30  # seconds; it normally answers in about one
WINDOWS_ATIRA = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local", "atira", "bin", "atira.cmd")
MODEL_DEFAULTS = {"QWEN_BASE_URL": "http://127.0.0.1:8765/qwen/v1", "QWEN_API_KEY": "local"}  # `atira models proxy`

NAME = r"([A-Za-z_][A-Za-z0-9_]*)"
ASSIGNMENT = re.compile(rf"^[ \t]*(?:\$env:{NAME}[ \t]*=[ \t]*|(?:export[ \t]+)?{NAME}=)", re.MULTILINE | re.IGNORECASE)
QUOTES = "'" + "".join(map(chr, (0x2018, 0x2019, 0x201A, 0x201B)))  # the four single quotes of PowerShell
POWERSHELL_STRING = re.compile(rf"[{QUOTES}]((?:[^{QUOTES}]|[{QUOTES}]{{2}})*)[{QUOTES}]")
POWERSHELL_DOUBLED = re.compile(rf"[{QUOTES}]([{QUOTES}])")
POSIX_PIECE = re.compile(r"""'([^']*)'|"((?:[^"\\]|\\[\s\S])*)"|\\(.)|([^\s'"\\;]+)""")
POSIX_ESCAPE = re.compile(r'\\([$`"\\]|\n)')  # all a backslash escapes inside double quotes


def parse_env_lines(text: str) -> dict[str, str]:
    r"""The variables that shell lines set, as {name: value}. Comments and anything else are skipped.

    The three syntaxes `atira scout --env` prints: PowerShell `$env:NAME = '...'`, where '' is a literal quote; POSIX
    `export NAME='...'`, where '\'' is one; and `NAME="..."` with backslash escapes. Nothing is expanded: a $ or a
    backtick in a value stays what it is. A value may be empty, and a quoted one may run over several lines.

    PowerShell also reads the typographic single quotes (U+2018, U+2019, U+201A, U+201B) as a quote, so the CLI
    doubles those too: a doubled one is that one character here as well.
    """
    variables, position = {}, 0
    while match := ASSIGNMENT.search(text, position):
        position = match.end()
        if match.group(1):  # PowerShell: one single-quoted string
            quoted = POWERSHELL_STRING.match(text, position)
            if quoted:
                variables[match.group(1)], position = POWERSHELL_DOUBLED.sub(r"\1", quoted.group(1)), quoted.end()
            continue
        pieces = []  # POSIX: quoted and bare pieces side by side make one word, so 'it'\''s' is it's
        while piece := POSIX_PIECE.match(text, position):
            body, position = piece.group(piece.lastindex), piece.end()
            pieces.append(POSIX_ESCAPE.sub(lambda escape: escape.group(1).strip("\n"), body)
                          if piece.lastindex == 2 else body)
        variables[match.group(2)] = "".join(pieces)
    return variables


def find_atira() -> str:
    """The atira CLI: $ATIRA_BIN, else the one on PATH, else where the Windows installer puts it."""
    override = os.environ.get("ATIRA_BIN")
    if override:
        return shutil.which(override) or override
    found = shutil.which("atira")
    if not found and os.name == "nt" and WINDOWS_ATIRA.is_file():
        found = str(WINDOWS_ATIRA)
    if not found:
        raise SystemExit("local_run: cannot find the atira CLI. Put it on PATH or set ATIRA_BIN.")
    return found


def stop_tree(process: subprocess.Popen) -> None:
    """Stop the CLI and what it started. On Windows atira.cmd is a cmd.exe that runs node, and node holds the pipes:
    killing only cmd.exe would leave `communicate` waiting for node for ever."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True)
    process.kill()
    try:
        process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def scout_output(timeout: float = SCOUT_TIMEOUT) -> str:
    """What the scout command prints. It holds the practice logins: keep it in memory, never print or store it."""
    scout = f"`atira {' '.join(SCOUT)}`"
    try:
        process = subprocess.Popen([find_atira(), *SCOUT], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
    except OSError as error:
        raise SystemExit(f"local_run: cannot run {scout}: {error}")
    try:
        output, errors = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        stop_tree(process)
        raise SystemExit(f"local_run: {scout} did not answer within {timeout:.0f} seconds. It stalls when it is called "
                         "several times in quick succession: wait a minute and run this again.")
    except BaseException:  # Ctrl+C: do not leave the CLI running
        stop_tree(process)
        raise
    if process.returncode != 0:  # its stdout stays unseen; stderr is the CLI's own explanation
        reason = errors.decode("utf-8", errors="replace").strip()
        raise SystemExit(f"local_run: {scout} failed with exit code {process.returncode}\n{reason}")
    return output.decode("utf-8-sig", errors="replace")


def site_count(env=os.environ) -> int | None:
    """How many websites the scouting run gives access to; None when CHALLENGE_SCOUTING is not that JSON."""
    try:
        return len(json.loads(env["CHALLENGE_SCOUTING"])["access"])
    except (KeyError, TypeError, ValueError):
        return None


def load_scouting() -> tuple[list[str], list[str]]:
    """Put the scouting run into os.environ: the names the scout command set, and the model names defaulted here.

    The model variables come from the scout output, else from your shell, else from MODEL_DEFAULTS.
    """
    variables = parse_env_lines(scout_output())
    os.environ.update(variables)
    if site_count() is None:
        raise SystemExit(f"local_run: `atira {' '.join(SCOUT)}` did not print a CHALLENGE_SCOUTING with an access "
                         f"list (it set {len(variables)} variables). Run it by hand to see why.")
    defaulted = [name for name in MODEL_DEFAULTS if name not in variables and not os.environ.get(name)]
    os.environ.update({name: MODEL_DEFAULTS[name] for name in defaulted})
    return list(variables), defaulted


def proxy_reachable(base_url: str, timeout: float = 2) -> bool:
    """Whether the host and port of the model URL accept a TCP connection."""
    try:
        parts = urlsplit(base_url)
        port = parts.port or (443 if parts.scheme == "https" else 80)
        with socket.create_connection((parts.hostname or "127.0.0.1", port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def site_list(text: str) -> str:
    """`a, b,` as the comma list the agent splits: a,b."""
    names = [name.strip() for name in text.split(",") if name.strip()]
    if not names:
        raise argparse.ArgumentTypeError("expected site ids separated by commas")
    return ",".join(names)


def arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--headed", action="store_true", help="show the browsers (default: HEADLESS=1 hides them)")
    parser.add_argument("--no-submit", action="store_true",
                        help="set AGENT_SKIP_SUBMIT=1: the agent stops before the bid form")
    parser.add_argument("--sites", type=site_list, metavar="ID,ID",
                        help="set AGENT_SITES: start only these site agents (default: all of them)")
    parser.add_argument("--max-steps", type=int, metavar="N",
                        help="set AGENT_MAX_STEPS: the most steps each site agent takes")
    parser.add_argument("--dump", type=Path, metavar="FILE",
                        help="set AGENT_DUMP: the agent writes its case file to FILE as JSON")
    parser.add_argument("--trace", type=Path, metavar="DIR",
                        help="set AGENT_TRACE: one file per agent turn in DIR, what the agent saw and what it replied")
    parser.add_argument("--log", type=Path, metavar="FILE",
                        help="also write the agent's stdout and stderr to FILE (UTF-8, overwritten on every run)")
    parser.add_argument("--check", action="store_true",
                        help="load the environment, print the variable NAMES, the number of sites and whether the "
                             "model proxy port is reachable, then exit without importing or running the agent")
    return parser.parse_args(argv)


def apply_flags(args: argparse.Namespace) -> list[str]:
    """Turn the flags into the variables the agent reads; what was set here, as NAME=value (none of it is secret)."""
    switches = {} if args.headed else {"HEADLESS": "1"}
    if args.no_submit:
        switches["AGENT_SKIP_SUBMIT"] = "1"
    if args.sites:
        switches["AGENT_SITES"] = args.sites
    if args.max_steps:
        switches["AGENT_MAX_STEPS"] = str(args.max_steps)
    # Absolute paths: the agent runs inside starter-kit, and neither file may end up in the package.
    if args.dump:
        switches["AGENT_DUMP"] = str(args.dump.resolve())
    if args.trace:
        switches["AGENT_TRACE"] = str(args.trace.resolve())
    if args.headed:
        os.environ.pop("HEADLESS", None)  # one left over in the shell would hide the browsers after all
    os.environ.update(switches)
    return [f"{name}={value}" for name, value in switches.items()]


def force_utf8() -> None:
    """UTF-8 on stdout and stderr: the websites are German, and a Windows console or pipe defaults to cp1252."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace", line_buffering=True)


class Tee:
    """A text stream that writes to the console and to the log file; everything else about it is the console's."""

    def __init__(self, console, log):
        self.console, self.log = console, log

    def write(self, text: str) -> int:
        self.log.write(text)
        return self.console.write(text)

    def flush(self) -> None:
        self.console.flush()
        self.log.flush()

    def __getattr__(self, name: str):
        return getattr(self.console, name)


def tee_to(path: Path) -> None:
    """From here on, what Python writes to stdout and stderr also goes to the log (line-buffered UTF-8).

    The log stays open until the process ends, so that what Python prints while shutting down is in it too. A child
    process that writes straight to the console (the browser driver) is not in it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    log = open(path, "w", encoding="utf-8", errors="backslashreplace", buffering=1)
    sys.stdout, sys.stderr = Tee(sys.stdout, log), Tee(sys.stderr, log)


def run_agent() -> int:
    """Import starter-kit/agent.py and run its main(), a coroutine function or a plain one: its return code."""
    sys.path.insert(0, str(STARTER_KIT))
    os.chdir(STARTER_KIT)
    agent_main = importlib.import_module("agent").main
    result = asyncio.run(agent_main()) if inspect.iscoroutinefunction(agent_main) else agent_main()
    if result is None:
        return 0
    return result if isinstance(result, int) else 1


def timed(run) -> int:
    """`run()`'s exit code, and a last line saying how long it took.

    The agent's own sys.exit() and a crash become exit codes here rather than at interpreter exit, so that the message
    or the traceback comes before the duration line. Ctrl+C is 130, without a traceback.
    """
    started = time.monotonic()
    try:
        code = run()
    except KeyboardInterrupt:
        print("local_run: interrupted", file=sys.stderr)
        code = 130
    except SystemExit as stop:
        code = stop.code
        if code is None:
            code = 0
        elif not isinstance(code, int):
            print(code, file=sys.stderr)
            code = 1
    except Exception:
        traceback.print_exc()
        code = 1
    minutes, seconds = divmod(time.monotonic() - started, 60)
    print(f"local_run: the agent ran for {int(minutes)}m{seconds:04.1f}s, exit code {code}", flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    args = arguments(argv)
    force_utf8()
    scouted, defaulted = load_scouting()
    switches = apply_flags(args)
    reachable = proxy_reachable(os.environ["QWEN_BASE_URL"])
    print(f"local_run: set from atira scout ({len(scouted)}): {', '.join(scouted)}")
    print(f"local_run: defaulted here: {', '.join(defaulted) or 'nothing'}")
    print(f"local_run: set by the flags: {' '.join(switches) or 'nothing'}")
    print(f"local_run: sites in CHALLENGE_SCOUTING's access list: {site_count()}")
    print(f"local_run: model proxy port (from QWEN_BASE_URL): {'reachable' if reachable else 'NOT reachable'}")
    if not reachable:
        print("local_run: warning: no model proxy is listening. Start it in another terminal: atira models proxy",
              file=sys.stderr)
    if args.check:
        return 0
    if args.log:
        tee_to(args.log)  # only now: nothing above this line is in the log
    return timed(run_agent)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)

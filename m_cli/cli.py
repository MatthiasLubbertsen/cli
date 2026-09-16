import getpass
import importlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from . import config, sync

BUILTINS = {
    "list", "add", "remove", "edit", "where",
    "push", "pull", "update", "help", "-h", "--help",
}


class UsageError(Exception):
    pass


def quote_extra_args(args):
    if sys.platform == "win32":
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(a) for a in args)


def build_steps(spec, extra_args):
    """Turn a command spec + cli args into the shell steps to run.

    If the spec has an "args" table, extra args fill those named
    placeholders positionally (unfilled ones keep their default) and get
    substituted into the run string(s). Otherwise extra args are just
    appended to the last step, unchanged.
    """
    run = spec["run"]
    steps = [run] if isinstance(run, str) else list(run)
    arg_defs = spec.get("args")
    if not arg_defs:
        return steps, extra_args

    names = list(arg_defs.keys())
    if len(extra_args) > len(names):
        raise UsageError(f"too many arguments, this command takes: {', '.join(names)}")
    params = dict(arg_defs)
    for param_name, value in zip(names, extra_args):
        params[param_name] = value
    try:
        steps = [step.format(**params) for step in steps]
    except KeyError as e:
        raise UsageError(f"command template uses unknown placeholder {e}")
    return steps, []


def run_steps(steps, extra_args):
    extra = quote_extra_args(extra_args) if extra_args else ""
    for i, step in enumerate(steps):
        cmd = step
        if extra and i == len(steps) - 1:
            cmd = f"{step} {extra}"
        print(f"$ {cmd}")
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            sys.exit(result.returncode)


def print_list(commands):
    if not commands:
        print("no commands configured yet. run `m add` to make one.")
        return
    width = max(len(name) for name in commands)
    for name, spec in sorted(commands.items()):
        desc = spec.get("description", "")
        print(f"  {name.ljust(width)}  {desc}")


def cmd_add(commands):
    name = input("command name: ").strip()
    if not name:
        print("name can't be empty")
        return
    if name in BUILTINS:
        print(f"'{name}' is a reserved name, pick another")
        return
    description = input("description (optional): ").strip()
    print("enter the shell command(s) to run, one per line.")
    print("blank line to finish (steps run in order, stopping if one fails):")
    steps = []
    while True:
        line = input("> ")
        if not line.strip():
            break
        steps.append(line)
    if not steps:
        print("no steps given, aborting")
        return
    commands[name] = {
        "description": description,
        "run": steps[0] if len(steps) == 1 else steps,
    }
    config.save_commands(commands)
    print(f"saved '{name}' to {config.config_path()}")
    maybe_auto_push(commands)


def cmd_remove(commands, name):
    if name not in commands:
        print(f"no such command: {name}")
        return
    del commands[name]
    config.save_commands(commands)
    print(f"removed '{name}'")
    maybe_auto_push(commands)


def cmd_edit():
    editor = os.environ.get("EDITOR") or ("notepad" if sys.platform == "win32" else "nano")
    subprocess.run([editor, str(config.config_path())])
    try:
        commands = config.load_commands()
    except json.JSONDecodeError as e:
        print(f"heads up: commands file has invalid json now ({e}), fix it before syncing")
        return
    maybe_auto_push(commands)


def maybe_auto_push(commands):
    app_cfg = config.load_app_config()
    if app_cfg.get("gist_id"):
        cmd_push(commands, quiet=True)


def get_token(app_cfg):
    token = os.environ.get("M_GIST_TOKEN") or app_cfg.get("token")
    if token:
        return token
    print("no github token configured for syncing commands.")
    print("make one (classic, with the 'gist' scope) at https://github.com/settings/tokens")
    token = getpass.getpass("paste it here (hidden): ").strip()
    if not token:
        raise UsageError("no token given, aborting")
    app_cfg["token"] = token
    config.save_app_config(app_cfg)
    return token


def cmd_push(commands, quiet=False):
    app_cfg = config.load_app_config()
    try:
        token = get_token(app_cfg)
        gist_id = app_cfg.get("gist_id") or sync.find_gist_id(token)
        content = json.dumps(commands, indent=2) + "\n"
        if gist_id:
            sync.push(token, gist_id, content)
        else:
            gist_id = sync.create_gist(token, content)
        if app_cfg.get("gist_id") != gist_id:
            app_cfg["gist_id"] = gist_id
            config.save_app_config(app_cfg)
        if not quiet:
            print(f"pushed {len(commands)} command(s) to https://gist.github.com/{gist_id}")
    except UsageError as e:
        print(str(e))
        if not quiet:
            sys.exit(1)
    except Exception as e:
        msg = f"push failed: {e}"
        print(f"(auto-sync {msg})" if quiet else msg)
        if not quiet:
            sys.exit(1)


def cmd_pull():
    app_cfg = config.load_app_config()
    try:
        token = get_token(app_cfg)
    except UsageError as e:
        print(str(e))
        sys.exit(1)
    gist_id = app_cfg.get("gist_id") or sync.find_gist_id(token)
    if not gist_id:
        print("no synced commands found yet. run `m push` on the machine that already has your commands.")
        sys.exit(1)
    if app_cfg.get("gist_id") != gist_id:
        app_cfg["gist_id"] = gist_id
        config.save_app_config(app_cfg)
    try:
        content = sync.pull(token, gist_id)
        new_commands = json.loads(content)
    except Exception as e:
        print(f"pull failed: {e}")
        sys.exit(1)
    config.save_commands(new_commands)
    print(f"pulled {len(new_commands)} command(s) from https://gist.github.com/{gist_id}")


def cmd_update():
    repo_root = Path(__file__).resolve().parent.parent
    if not (repo_root / ".git").exists():
        print(f"can't find a git checkout at {repo_root}.")
        print("`m update` only works when m was installed with `pip install -e .` from a git clone.")
        sys.exit(1)

    print(f"updating m from {repo_root} ...")
    result = subprocess.run(["git", "-C", str(repo_root), "pull", "--ff-only"])
    if result.returncode != 0:
        print("git pull failed, go resolve it manually in that folder.")
        sys.exit(result.returncode)

    subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(repo_root), "--quiet"])

    importlib.reload(config)
    commands = config.load_commands()
    added = [name for name in config.DEFAULT_COMMANDS if name not in commands]
    if added:
        for name in added:
            commands[name] = config.DEFAULT_COMMANDS[name]
        config.save_commands(commands)
        print(f"added new default command(s): {', '.join(added)}")

    print("m is up to date.")


def print_help():
    print("m - your personal shortcut runner")
    print()
    print("usage:")
    print("  m                 list your commands")
    print("  m <name> [args]   run a command")
    print("  m add             add a new command interactively")
    print("  m remove <name>   remove a command")
    print("  m edit            open the commands file in your editor")
    print("  m where           print the path to the commands file")
    print("  m push            sync your commands up to a private github gist")
    print("  m pull            sync your commands down from that gist")
    print("  m update          pull the latest m code (needs a git install) and reinstall")


def main():
    argv = sys.argv[1:]
    commands = config.load_commands()

    if not argv:
        print_list(commands)
        return

    name, rest = argv[0], argv[1:]

    if name in ("help", "-h", "--help"):
        print_help()
        return
    if name == "list":
        print_list(commands)
        return
    if name == "add":
        cmd_add(commands)
        return
    if name == "remove":
        if not rest:
            print("usage: m remove <name>")
            sys.exit(1)
        cmd_remove(commands, rest[0])
        return
    if name == "edit":
        cmd_edit()
        return
    if name == "where":
        print(config.config_path())
        return
    if name == "push":
        cmd_push(commands)
        return
    if name == "pull":
        cmd_pull()
        return
    if name == "update":
        cmd_update()
        return

    if name not in commands:
        print(f"no command called '{name}'. try `m list` or `m add`.")
        sys.exit(1)

    try:
        steps, remaining = build_steps(commands[name], rest)
    except UsageError as e:
        print(str(e))
        sys.exit(1)
    run_steps(steps, remaining)


if __name__ == "__main__":
    main()

import os
import shlex
import subprocess
import sys

from . import config

BUILTINS = {"list", "add", "remove", "edit", "where", "help", "-h", "--help"}


def quote_extra_args(args):
    if sys.platform == "win32":
        return subprocess.list2cmdline(args)
    return " ".join(shlex.quote(a) for a in args)


def run_steps(steps, extra_args):
    if isinstance(steps, str):
        steps = [steps]
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


def cmd_remove(commands, name):
    if name not in commands:
        print(f"no such command: {name}")
        return
    del commands[name]
    config.save_commands(commands)
    print(f"removed '{name}'")


def cmd_edit():
    editor = os.environ.get("EDITOR") or ("notepad" if sys.platform == "win32" else "nano")
    subprocess.run([editor, str(config.config_path())])


def print_help():
    print("m - your personal shortcut runner")
    print()
    print("usage:")
    print("  m                 list your commands")
    print("  m <name> [args]   run a command (extra args are appended to its last step)")
    print("  m add             add a new command interactively")
    print("  m remove <name>   remove a command")
    print("  m edit            open the commands file in your editor")
    print("  m where           print the path to the commands file")


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

    if name not in commands:
        print(f"no command called '{name}'. try `m list` or `m add`.")
        sys.exit(1)

    run_steps(commands[name]["run"], rest)


if __name__ == "__main__":
    main()

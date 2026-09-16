# m

a tiny personal cli that turns your long, annoying commands into one short word.

```
$ m redeploy
$ docker compose down
$ git pull
$ docker compose up -d
```

works the same on ubuntu and windows. no fancy dependencies, just python.

## install

needs python 3.8+.

**ubuntu / linux**

```bash
sudo git clone https://github.com/MatthiasLubbertsen/cli.git /opt/m-cli
sudo chown -R "$USER":"$USER" /opt/m-cli
pipx install -e /opt/m-cli
```

(no `pipx`? `pip install --user -e /opt/m-cli` works too)

The `chown` matters: `m update` does a plain `git pull` in that folder later, and you don't want to need `sudo` for that every time.

**windows** (powershell or cmd)

```powershell
git clone https://github.com/MatthiasLubbertsen/cli.git
cd cli
py -m pip install --user -e .
```

Doesn't matter where you put the folder, `m update` finds it later by asking Python where the installed package lives, not by remembering a path. Make sure your Python `Scripts` folder is on `PATH` so the `m` command is found (the installer will warn you if it isn't).

Either way, once installed you get an `m` command anywhere.

## usage

```
m                 list your commands
m <name> [args]   run a command
m add             add a new command, interactively
m remove <name>   remove a command
m edit            open the commands file in your editor
m where           print the path to the commands file
m push            sync your commands up to a private github gist
m pull            sync your commands down from that gist
m update          pull the latest m code (needs a git install) and reinstall
```

Your commands live in a plain JSON file (`m where` shows exactly where):

- ubuntu/linux: `~/.config/m/commands.json`
- windows: `%APPDATA%\m\commands.json`

## adding a command

Easiest way, just run `m add` and answer the prompts. Or edit the JSON file directly (`m edit`), e.g.:

```json
{
  "redeploy": {
    "description": "pull latest code and restart the docker compose stack",
    "run": ["docker compose down", "git pull", "docker compose up -d"]
  },
  "boot": {
    "description": "push a file to a connected micropython board",
    "run": "mpremote resume fs cp {file} :{file}",
    "args": {"file": "boot.py"}
  }
}
```

`run` can be a single string, or a list of steps that run in order (stops if one fails, just like `&&`).

There's two ways extra arguments you type after the command name get used:

**no `args` field** &rarr; they just get tacked onto the end of the last step. With the config above:

```
m redeploy --build
```

runs `docker compose up -d --build` for the last step.

**with an `args` field** &rarr; they fill in named `{placeholders}` in `run`, in the order `args` lists them, positionally. Anything you don't pass keeps its default. With the `boot` command above:

```
m boot            # -> mpremote resume fs cp boot.py :boot.py
m boot main.py    # -> mpremote resume fs cp main.py :main.py
```

Want the local file and the remote path to move independently? Use two placeholders:

```json
"boot": {
  "run": "mpremote resume fs cp {local} :{remote}",
  "args": {"local": "boot.py", "remote": "boot.py"}
}
```

```
m boot main.py other.py   # -> mpremote resume fs cp main.py :other.py
```

These two examples ship as the defaults the first time you run `m`, so you can try it immediately and tweak from there.

## syncing commands across machines

`m push` and `m pull` sync your `commands.json` through a private GitHub gist, so the same commands show up everywhere.

First time, on any machine:

```
m push
```

It'll ask for a GitHub personal access token (classic, with the `gist` scope — make one at https://github.com/settings/tokens) and create a private gist to hold your commands. The token is saved locally at `m where`'s sibling file (never committed anywhere).

On another machine, use the same GitHub account's token, then:

```
m pull
```

It finds your gist automatically (no need to copy a gist ID around) and overwrites your local commands with it.

Once a machine has synced once (it remembers the gist), `m add`, `m remove`, and `m edit` auto-push for you, so you don't have to think about it. It's just a JSON blob though: last push wins, there's no merging of conflicting edits.

Prefer not to store the token on disk? Set the `M_GIST_TOKEN` environment variable instead and it'll be used over the saved one.

## updating m itself

If `m` was installed with `pip install -e .` from a git clone (that's what the install steps above do), run:

```
m update
```

It runs `git pull --ff-only` in whatever folder `m` was installed from — wherever that is, it finds it by asking Python where the package actually lives, so it works whether that's `/opt/m-cli` on Ubuntu or some folder on Windows you don't remember. It also re-runs the install step in case dependencies changed, and adds any brand-new default commands the update shipped (without touching ones you've already customized).

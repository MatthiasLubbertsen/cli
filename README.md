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
git clone <this-repo-url>
cd cli
pipx install -e .
```

(no `pipx`? `pip install --user -e .` works too)

**windows** (powershell or cmd)

```powershell
git clone <this-repo-url>
cd cli
py -m pip install --user -e .
```

Make sure your Python `Scripts` folder is on `PATH` so the `m` command is found (the installer will warn you if it isn't).

Either way, once installed you get an `m` command anywhere.

## usage

```
m                 list your commands
m <name> [args]   run a command (extra args get appended to its last step)
m add             add a new command, interactively
m remove <name>   remove a command
m edit            open the commands file in your editor
m where           print the path to the commands file
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
    "description": "push boot.py to a connected micropython board",
    "run": "mpremote resume fs cp boot.py :boot.py"
  }
}
```

`run` can be a single string, or a list of steps that run in order (stops if one fails, just like `&&`).

Extra args you pass get appended to the last step, so with the config above:

```
m redeploy --build
```

runs `docker compose up -d --build` for the last step.

These two examples ship as the defaults the first time you run `m`, so you can try it immediately and tweak from there.

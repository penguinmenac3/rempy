# rempy

## Install

Simply install it via pip.
```bash
pip install rempy
```

## Usage

You can run a variety of scripts in various places. There are two limitations:
1. Scripts cannot expect any user input.
2. Outputs of scripts are only shown once a newline is entered.

### SSH Remote

For executing scripts via ssh simply use the rempy command and provide a hostname separated by an `@` from your scriptname. In case you do not have a config for the remote, a remote execution folder is required separated by a `:` (here `/home/$USER/Testing`). Your code will then be stored and executed in a subfolder of that remote_path that has the same basename as your current working directory. Here the folder I am in is rempy, so the remote folder, where my code will be actually stored is `/home/$USER/Testing/rempy`.
```bash
# remote script execution
rempy tests/hello.py@example.com:/home/$USER/Testing
# or module style
rempy -m tests.hello@example.com:/home/$USER/Testing
```

Do you need a special package name on the remote. So you do not like the basename of your local workplace. You can use `--package_name`. The following would be equivalent to the above.
```bash
# remote script execution
rempy tests/hello.py@example.com:/home/$USER/Testing/rempy --package_name="."
```

### Remote Hosts Config

Are you lazy and do not want to provide the `remote_path` every time?
I am. So from now on we will use the config and not provide it anymore.

Create a `~/.rempy_hosts.json` with the following content. The top level is a dictionary with the hostnames as keys. Beneath it is a dictionary containing the remote path, leaving space for future expansion.
```json
{
    "example.com": {
        "remote_path": "/home/example/Testing"
    }
}
```


### Pre Launch

If you have any tasks that need to happen before executing your code.
```bash
rempy -m tests.hello@example.com --pre_launch="pip install -r requirements.txt"
```

### Conda Environments

In case your code needs to run in a specific conda env use `--conda`.
```bash
rempy -m tests.hello@example.com --conda base
```
For this to work, you need to tell the remote config, where to find conda, as the bashrc is not loaded in non-interactive mode.
```json
{
    "example.com": {
        "remote_path": "/home/example/Testing",
        "conda_init": "source '/home/example/miniconda3/etc/profile.d/conda.sh'",
    }
}
```

### Any Launcher

Run non python scripts via any launcher, e.g. bash, using `--launcher`.
```bash
rempy --launcher="bash" tests/hello.sh@example.com
```

### Remote Debugging Python

You can attach your visual studio python debugger by specifying the debug port using `--debug`. **Important: Please use a random port that is not used, otherwise you will get collisions with other users!**
```bash
rempy tests/hello.py@example.com --debug=24978
# or
rempy -m tests.hello@example.com --debug=24978
```

A corresponding `.vscode/launch.json` for vscode would look like this.
```json
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 24978
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "."
                }
            ]
        }
    ]
}
```


### SLURM

You can also run jobs on a slurm cluster. This can be combined with any of the previous arguments (even debugging!).

**Words of WARNING for cluster users:**
1. When debugging, be aware, that you block resources on the cluster until you cancel the job rempy creates or you attach your debugger. Also after detaching your debugger, your job might still be blocking resources, so make sure it ends and if not kill it with `scancel`.
2. Read the respective instructions and guidelines on how to use the cluster from your provider. They might have restrictions on where to put code, outputs, etc. so make sure you adhere to them.
3. This script takes no warranties for anything that you mess up. We simply execute a srun command for you.

Under the hood cluster support for rempy is implemented by connecting to the head node via ssh and then running srun there with the arguments provided in slurm.json, the final command is then the provided one as without slurm.

Submiting your code to run on the cluster is as easy as passing a file containing the slurm args or a string containing them directly. (A file is highly encouraged!)
```bash
rempy tests/hello.py@example.com --slurm_args slurm.txt
```

An example `slurm.txt` can contain any arguments.
```bash
--job-name=hello_world
--partition=batch
--ntasks=1
--gpus-per-task=1
--cpus-per-gpu=8
--mem=24G
```

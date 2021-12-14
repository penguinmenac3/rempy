import argparse
import json
import os

from rempy.runtime.remote_cli import RemoteCLI
from rempy.sync.manager import SyncManager


def get_env(name):
    if name in os.environ:
        return os.environ[name]
    else:
        return None

def get_hosts_config():
    config_path = os.path.join(os.environ["HOME"], ".rempy_hosts.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = f.read()
        return json.loads(data)
    return {}


def parse_args():
    USER = get_env("USER")
    parser = argparse.ArgumentParser()
    parser.add_argument("script@host[:/remote/path]", help="")
    parser.add_argument("--user", default=USER, required=USER is None, help="Specifies as what user to connect to the remote. Default will be $USER.")
    parser.add_argument("--debug", action="store_true", help="Launches the code in debug mode (for VSCode) and forwards the debugger ports to localhost. See remote debugging in the readme.")
    parser.add_argument("--dir", default=os.getcwd(), required=False, help="Defines which folder (and all subfolders) should be mirrored to the remote. Default is the current working directory.")
    parser.add_argument("--sync", action="store_true", help="Set this flag if you do not want ot execute a script on the remote but just mirror the directory.")
    parser.add_argument("--launcher", default="python", required=False, help="What command is used to execute the provided file. Defaults to 'python'.")
    parser.add_argument("--interface", default="ssh", required=False, help="How to connect to the remote. Currently 'ssh' and 'slurm' are supported. Defaults to 'ssh'.")
    parser.add_argument("--interface_args", default="", required=False, help="Either a path or a string containing the arguments to pass to the remote interface command (e.g. srun for slurm).")
    parser.add_argument("--watch", default=0, type=int, required=False, help="When larger than 0 continously syncs files every N seconds. Like sync does not execute any script.")
    args, other_args = parser.parse_known_args()
    args = vars(args)
    args["script"], args["host"], args["remote_path"] = parse_main(args['script@host[:/remote/path]'])
    del args['script@host[:/remote/path]']
    args["args"] = other_args
    return args


def parse_main(url):
    tokens = url.split("@")
    if len(tokens) != 2:
        print("ERROR: You must provide a file and a host via: 'script@host[:/remote/path]'.")
        if len(tokens) == 3:
            print("Detected multiple @ symbols. Did you use main.py@user@host?")
            print("  In that case use --user for your username.")
            print("  Example: main.py@example.com --user=foo")
        else:
            print("  Example: main.py@example.com")
        os._exit(0)
    script, host = tokens
    tokens = host.split(":")
    host = tokens[0]
    if len(tokens) > 2:
        print("ERROR: You provided more than one remote path. Make sure you only provide one.")
        print("  Example: main.py@example.com:/home/foo/Code")
        os._exit(0)
    elif len(tokens) == 2:
        remote_path = tokens[1]
    else:
        config = get_hosts_config()
        if host in config and "remote_path" in config[host]:
            remote_path = config[host]["remote_path"]
        else:
            print("ERROR: No remote path provided and no valid configuration found.")
            print("  Option 1: Provide a remote path via the command line.")
            print("  Example: main.py@example.com:/home/foo/Code")
            print("  Option 2: Create a config file in $HOME/.rempy_hosts.json containing an entry for your host and the entry contains a remote_path.")
            print("  Example Config: {'example.com': {'remote_path':'/path/on/remote'}}")
            os._exit(0)
    return script, host, remote_path


def run_remote(host, user, remote_path, interface, interface_args, launcher, script, debug, **ignore):
    if os.path.exists(interface_args):
        if interface_args.endswith(".slurm"):
            interface = "slurm"
            print("Overwrite interface to 'slurm', since a slurm config was provided.")
        with open(interface_args, "r") as f:
            interface_args = f.read()
    cli = RemoteCLI(host, user, remote_path, interface, interface_args)
    cli.execute_script(script, launcher, debug)
    cli.close()


def sync_remote(host, user, dir, remote_path, watch, **ignore):
    sync = SyncManager(host, user, dir, remote_path)
    if watch > 0:
        sync.watch(watch)
    else:
        sync.sync()


def main():
    args = parse_args()
    sync_remote(**args)
    if not args["sync"] and args["watch"] <= 0:
        run_remote(**args)

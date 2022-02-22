import argparse
import json
import os

from rempy.runtime.remote_cli import remoteExecute
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
    parser.add_argument("-m", action="store_true", help="Run python in module mode. Shorthand for '--launcher=\"python -m\"'. Overwrites --launcher argument.")
    parser.add_argument("--user", default=USER, required=USER is None, help="Specifies as what user to connect to the remote. Default will be $USER.")
    parser.add_argument("--debug", default=0, type=int, help="Specify a debug port. This causes the code to be launched in (VSCode) debug mode and ports are forwarded to localhost.")
    parser.add_argument("--dir", default=os.getcwd(), required=False, help="Defines which folder (and all subfolders) should be mirrored to the remote. Default is the current working directory.")
    parser.add_argument("--sync", action="store_true", help="Set this flag if you do not want ot execute a script on the remote but just mirror the directory.")
    parser.add_argument("--launcher", default="python", required=False, help="What command is used to execute the provided file. Defaults to 'python'.")
    parser.add_argument("--interface", default="ssh", required=False, help="How to connect to the remote. Currently 'ssh' and 'slurm' are supported. Defaults to 'ssh'.")
    parser.add_argument("--ssh_args", default="", required=False, help="A string containing args to pass to the respective command or a path to a file containing the string. Defaults to an empty string.")
    parser.add_argument("--slurm_args", default="", required=False, help="A string containing args to pass to the respective command or a path to a file containing the string. Defaults to an empty string.")
    parser.add_argument("--watch", default=0, type=int, required=False, help="When larger than 0 continously syncs files every N seconds. Like sync does not execute any script.")
    parser.add_argument("--pre_launch", default="", type=str, required=False, help="A command that is executed in the working directory before running your code.")
    parser.add_argument("--package_name", default=None, required=False, help="A custom name for the folder in remote_path where to store the code. (If you do not want a subfolder use '.'!)")
    parser.add_argument("--conda", default=None, required=False, help="Specify a conda environment to use.")
    parser.add_argument("--logfile", default=None, required=False, help="Specify a file where to log all outputs of the main process.")
    args, other_args = parser.parse_known_args()
    args = vars(args)
    if args["slurm_args"] != "":
        args["interface"] = "slurm"
    if args["m"]:
        args["launcher"] = "python -m"
    args["script"], args["host"], args["remote_path"] = parse_main(args['script@host[:/remote/path]'])
    if args["package_name"] is None:
        args["package_name"] = os.path.basename(os.path.abspath(args["dir"]))
    del args['script@host[:/remote/path]']
    args["args"] = " ".join(other_args)
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


def try_file_reading(args):
    if os.path.exists(args):
        with open(args, "r") as f:
            args = f.read().replace("\n", " ")
    return args


def run_remote(host, user, remote_path, interface, ssh_args, slurm_args, launcher, script, args, debug, pre_launch, package_name, conda, logfile, **ignore):
    if conda is not None:
        config = get_hosts_config()
        if host in config and "conda_init" in config[host]:
            conda_init = config[host]["conda_init"]
        else:
            print("ERROR: No conda_init in host configuration found.")
            print("  Create a config file in $HOME/.rempy_hosts.json containing an entry for your host and the entry contains a conda_init.")
            print("  Example Config: {'example.com': {'conda_init': 'source \\'/home/example/miniconda3/etc/profile.d/conda.sh\\''")
            os._exit(0)
        if pre_launch != "":
            pre_launch = f"&& {pre_launch}"
        pre_launch = f"{conda_init} && conda activate {conda}{pre_launch}"
    ssh_args = try_file_reading(ssh_args)
    slurm_args = try_file_reading(slurm_args)
    remote_path = os.path.join(remote_path, package_name)
    remoteExecute(host, user, remote_path, script, args, launcher, debug, interface, ssh_args, slurm_args, pre_launch, logfile)


def sync_remote(host, user, dir, remote_path, watch, package_name, **ignore):
    sync = SyncManager(host, user, dir, remote_path, package_name)
    if watch > 0:
        sync.watch(watch)
    else:
        sync.sync()


def main():
    args = parse_args()
    sync_remote(**args)
    if not args["sync"] and args["watch"] <= 0:
        run_remote(**args)

import entangle
import base64
import os
import sys
import json
import datetime
import time
from rempy.lib.compute_patch import pack_patch


CONFIG_PATH = os.path.join(os.environ["userprofile"] if os.name == "nt" else os.environ["HOME"], ".rempy-client.json")
DEFAULT_PORT = 24454


def config():
    conf = {
        "user": {
            "name": "deepthought",
            "password": "42"
        },
        "commit": "Run: $NAME_$TIMESTAMP",
        "tag": "$NAME_$TIMESTAMP",
        "name-required": True,
        "aliase": {
            "example": "localhost:24454"
        }
    }
    with open(CONFIG_PATH, "w") as f:
        f.write(json.dumps(conf, indent=4, sort_keys=True))
    print("Created basic config at {}. You should change at least the password!".format(CONFIG_PATH))


def parse_args(args, conf):
    host = args[0]
    if "aliase" in conf and host in conf["aliase"]:
        host = conf["aliase"][host]
    port = DEFAULT_PORT
    if ":" in host:
        tmp = host.split(":")
        assert len(tmp) == 2, "Only one : to separate hostname and port is allowed!"
        host, port = tmp[0], int(tmp[1])

    env = {
        "mode": "shell",
        "reconnect": False,
        "name": "",
        "kill": False
    }
    reconnect = False
    idx = 1
    if args[idx] == "-r":  # Reconnect
        command = None
        reconnect = True
        env["reconnect"] = args[idx + 1]
    if args[idx] == "--kill":  # kill
        command = None
        reconnect = True
        env["kill"] = True
        env["reconnect"] = args[idx + 1]

    if args[idx] == "--gpu":  # GPU
        env["gpu"] = args[idx + 1]
        idx = idx + 2
    if args[idx] == "--name":
        env["name"] = args[idx + 1]
        idx = idx + 2
    elif conf["name-required"]:
        while env["name"] == "" and not reconnect:
            env["name"] = input("A name for your run is required! > ")

    if args[idx] == "--no-commit" or reconnect:
        if "commit" in conf:
            del conf["commit"]
        if "tag" in conf:
            del conf["tag"]
        idx = idx + 1
    if not "name" in env and ("commit" in conf or "tag" in conf):
        raise RuntimeError("For commiting or tagging a name is mandatory!")
    elif "tag" in conf and not "commit" in conf:
        raise RuntimeError("You must enable commit in order to activate tagging.")

    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H.%M.%S')
    if "commit" in conf:
        commit_msg = conf["commit"].replace("$NAME", env["name"]).replace("$TIMESTAMP", timestamp)
        os.system("git add --all")
        os.system("git commit -m \"{}\"".format(commit_msg))
    if "tag" in conf:
        tag_msg = conf["tag"].replace("$NAME", env["name"]).replace("$TIMESTAMP", timestamp)
        # TODO implement tagging

    if reconnect:
        command = None
    elif args[idx] == "--push":  # simply push an update
        command = []
        env["mode"] = "python"
    elif args[idx] == "-m":  # Python Module
        command = ["python"] + args[idx:]
        env["mode"] = "python"
    elif args[idx].endswith(".py"):  # Python Script
        command = ["python"] + args[idx:]
        env["mode"] = "python"

    elif args[idx].endswith(".sh"):  # Bash Script
        command = ["sh"] + args[idx:]
        env["mode"] = "shell"

    elif args[idx].endswith(".js"):  # Nodejs Script
        command = ["nodejs"] + args[idx:]
        env["mode"] = "nodejs"

    else:  # Anything else is unknown and passed through
        command = args[idx:]

    return host, port, command, env


def main(args):
    if not os.path.exists(CONFIG_PATH):
        print("You must create a config first via 'rempy config-client'.")
        return
    with open(CONFIG_PATH, "r") as f:
        conf = json.loads(f.read())
    cwd = os.path.normpath(os.path.abspath("."))
    project_name = cwd.replace("\\", "/").split("/")[-1]

    host, port, command, env = parse_args(args, conf)
    user = conf["user"]["name"]
    password = conf["user"]["password"]

    # Connect to server
    try:
        entanglement = entangle.connect(host=host, port=port, password=password, user=user)
    except KeyboardInterrupt:
        return
    entanglement.protocol = "rempy"

    def rprint(*args, **kwargs):
        print(*args, **kwargs)
    entanglement.rempy_print = rprint
    entanglement.rempy_project_name = project_name
    entanglement.rempy_env = env

    if not env["reconnect"]:
        # Wait for file_hash_map from server
        server_hashes = entanglement.get("rempy_hash_map")

        # Pack patch
        ignore_list = []
        if os.path.exists(".ignore"):
            with open(".ignore", "r") as f:
                ignore_list = [q.rstrip() for q in f.readlines()]

        patch_file, deleted = pack_patch(cwd, server_hashes, forbidden_list=ignore_list)
        with open(patch_file, mode='rb') as file:
            patch_file_content = file.read()
        os.remove(patch_file)

        # Encode
        patch_file_content = base64.encodestring(patch_file_content).decode('ascii')
        print("Patch Size: {}".format(len(patch_file_content)))

        # Send patchfile and list of deleted files to server
        entanglement.rempy_patch = (patch_file_content, deleted)

        # Tell server what file to run and how and then forward output/input until connection is closed by server
        entanglement.rempy_command = command
    try:
        while entanglement.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pname = entanglement.rempy_pname
        action = input("\nDetach only? [Y/n]\n")
        if action != "n" and action != "N":
            entanglement.close()
            print()
            print("Detached.")
            if port != DEFAULT_PORT:
                print("Reconnect by:    rempy {}:{} -r {}".format(host, port, pname))
            else:
                print("Reconnect by:    rempy {} -r {}".format(host, pname))
        else:
            env["kill"] = True
            entanglement.rempy_env = env
            entanglement.join()
            entanglement.close()
            print()
            print("Killed {} on {}".format(pname, host))

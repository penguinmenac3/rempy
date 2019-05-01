import entangle
import base64
import os
from rempy.lib.compute_patch import pack_patch


def parse_args(args):
    host = args[0]
    port = 24454
    if ":" in host:
        tmp = host.split(":")
        assert len(tmp) == 2, "Only one : to separate hostname and port is allowed!"
        host, port = tmp[0], int(tmp[1])
    
    env = {
        "mode": "shell",
        "gpus": "all",
        "reconnect": False
    }

    if args[1] == "-r":  # Reconnect
        command = None
        env["reconnect"] = args[2]

    elif args[1] == "-m":  # Python Module
        command = ["python"] + args[1:]
        env["mode"] = "python"
    elif args[1].endswith(".py"):  # Python Script
        command = ["python"] + args[1:]
        env["mode"] = "python"
    
    elif args[1].endswith(".sh"):  # Bash Script
        command = ["sh"] + args[1:]
        env["mode"] = "shell"

    elif args[1].endswith(".js"):  # Nodejs Script
        command = ["nodejs"] + args[1:]
        env["mode"] = "nodejs"
    
    else:  # Anything else is unknown and passed through
        command = args[1:]

    return host, port, command, env


def main(args):
    cwd = os.path.normpath(os.path.abspath("."))
    project_name = cwd.replace("\\", "/").split("/")[-1]

    host, port, command, env = parse_args(args)
    password = "42"

    # Connect to server
    entanglement = entangle.connect(host=host, port=port, password=password)
    def rprint(*args, **kwargs):
        print(*args, **kwargs)
    entanglement.print = rprint
    entanglement.project_name = project_name
    entanglement.env = env

    if not env["reconnect"]:
        # Wait for file_hash_map from server
        server_hashes = entanglement.get("hash_map")

        # Pack patch
        patch_file, deleted = pack_patch(cwd, server_hashes)
        with open(patch_file, mode='rb') as file:
            patch_file_content = file.read()
        os.remove(patch_file)

        # Encode
        patch_file_content = base64.encodestring(patch_file_content).decode('ascii')
        print("Patch Size: {}".format(len(patch_file_content)))

        # Send patchfile and list of deleted files to server
        entanglement.patch = (patch_file_content, deleted)

        # Tell server what file to run and how and then forward output/input until connection is closed by server
        entanglement.command = command

    entanglement.join()

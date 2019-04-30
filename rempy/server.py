import entangle
import base64
import os
import shutil
from rempy.lib.compute_patch import get_files_hash_map, apply_patch

processes = {}

def run(entanglement):
    project_name = entanglement.get("project_name")
    project_path = os.path.join(os.environ["REMPY_HOME"], project_name)
    if not os.path.exists(project_path):
        os.makedirs(project_path)
    env = entanglement.get("env")
    
    if not env["reconnect"]:
        hash_map = get_files_hash_map(project_path)
        entanglement.hash_map = hash_map

        # Wait for patch and to delete
        patch_file_content, deleted = entanglement.get("patch")

        # Decode
        patch_file_content = base64.decodestring(patch_file_content.encode("ascii"))
        patch_path = project_path + ".zip"
        with open(patch_path, mode='wb') as file:
            file.write(patch_file_content)

        # Delete files
        for f in deleted:
            d = os.path.join(project_path, f)
            if os.path.isdir(d):
                print("Remove dir: {}".format(d))
                shutil.rmtree(d)
            elif os.path.exists(d):
                print("Remove file: {}".format(d))
                os.remove(d)
            else:
                print("Ignored: {}".format(d))
        apply_patch(project_path, project_path)

        # Wait for instructions what to run and how
        command = entanglement.get("command")

        # Start program
        # TODO

    # Forward outputs/inputs to network
    rprint = entanglement.remote_fun("print")
    rprint("Hello World!")
    # TODO

    # Close connection
    entanglement.close()

def main(args):
    print("Server")
    host = "*"
    port = 24454
    password = "42"
    
    # Start a listener for connections
    entangle.listen(host=host, port=port, password=password, callback=run)

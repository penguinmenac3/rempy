from rempy.lib.compute_patch import pack_patch

def main(args):
    print("Client")
    cwd = "."

    # Connect to server
    # TODO

    # Wait for file_hash_map from server
    # TODO
    server_hashes = {}

    # Pack patch
    patch_file, deleted = pack_patch(cwd, server_hashes)

    # Send patchfile and list of deleted files to server
    # TODO

    # Tell server what file to run and how and then forward output/input until connection is closed by server
    # TODO

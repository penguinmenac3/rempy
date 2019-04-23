from rempy.lib.compute_patch import get_files_hash_map, apply_patch

def run(connection):
    project_path = "."
    files_hash_map = get_files_hash_map(project_path)

    # Send hasn map to client
    # TODO

    # Wait for patch and to delete
    # TODO
    patch_path, deleted = "foo.zip", []

    # Delete files
    # TODO
    apply_patch(patch_path, project_path)

    # Wait for instructions what to run and how
    # TODO

    # Run program and forward outputs/inputs to network
    # TODO

    # Close connection
    # TODO

def main(args):
    print("Server")
    
    # Start a listener for connections
    # TODO

"""doc
# patcher.py

> Implements a tool to compute patches given a state.

Simply call the pack_patch function with a path and a dict containing the hashes from the server.
The server hashes will be stored in a ".md5.json", which is part of each patch.
This way the server knows its hashes without any software required on the server.

```
server_hashes = {"fname": "md5"}
folder = "."
patch_file_path, deleted, hashes = pack_patch(folder, server_hashes, forbidden_list=[])
# patch_file_path is the path to a zip with the changed files.
# deleted is a list of deleted files.
# hashes are the hashes both sides have once the patch is applied.
```

License: MIT (see main license)
Authors:
* Michael Fuerst (Lead)
"""
import os
import json
import shutil
import hashlib
import zipfile
import time
import datetime


PYTHON_IGNORE_LIST = ["__pycache__", "*.pyc", ".ipynb_checkpoints", ".git", ".svn", ".hg", "CSV", ".DS_Store", "*.egg-info"]


def __md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def __ignore(candidate, forbidden_list):
    # Parse list to find simple placeholder notations
    start_list = []
    end_list = []
    for item in forbidden_list:
        if item.startswith("*"):
            end_list.append(item.replace("*", ""))
        if item.endswith("*"):
            start_list.append(item.replace("*", ""))
    # Test
    ignore_file = candidate in forbidden_list
    for item in start_list:
        ignore_file |= candidate.startswith(item)
    for item in end_list:
        ignore_file |= candidate.endswith(item)
    return ignore_file


def __get_syncignore(folder):
    syncignore = []
    ignore_file = os.path.join(folder, ".syncignore")
    if os.path.exists(ignore_file):
        with open(ignore_file, "r") as f:
            syncignore = f.read().split("\n")
    return syncignore


def __get_all_files(root, forbidden_list):
    all_files = []
    root_with_sep = root + os.sep
    for path, subdirs, files in os.walk(root):
        local_syncignore = __get_syncignore(path)
        local_syncignore.extend(forbidden_list)
        files = [x for x in files if not __ignore(x, local_syncignore)]
        subdirs[:] = [x for x in subdirs if not x.startswith(".") and not __ignore(x, local_syncignore)]
        for name in files:
            all_files.append(os.path.join(path, name).replace(root_with_sep, "").replace(os.sep, "/"))
    return all_files


def __get_empty_folders(root, forbidden_list):
    forbidden_list.extend(PYTHON_IGNORE_LIST)
    empty_folders = []
    for path, subdirs, files in os.walk(root):
        files = [x for x in files if not __ignore(x, forbidden_list)]
        subdirs[:] = [x for x in subdirs if not x.startswith(".") and not __ignore(x, forbidden_list)]
        if len(files) == 0:
            empty_folders.append(path)
    return empty_folders


def __diff(should_be, current_state, verbose=False):
    changed = []
    deleted = []
    for k in should_be:
        if not k in current_state:
            changed.append(k)
            if verbose:
                print("Added {}".format(k))
        elif current_state[k] != should_be[k]:
            changed.append(k)
            if verbose:
                print("Changed {}: {} <-> {}".format(k, current_state[k], should_be[k]))
    for k in current_state:
        if not k in should_be:
            deleted.append(k)
            if verbose:
                print("Deleted {}".format(k))
    return changed, deleted


def get_files_hash_map(root, forbidden_list):
    forbidden_list.extend(PYTHON_IGNORE_LIST)
    files = __get_all_files(root, forbidden_list)
    md5s = [__md5(os.path.join(root, f).replace(os.sep, "/")) for f in files]
    hash_map = dict(zip(files, md5s))
    return hash_map


def pack_patch(folder, server_hashes, forbidden_list=[], verbose=True):
    should_be = get_files_hash_map(folder, forbidden_list=forbidden_list)
    changed, deleted = __diff(should_be, server_hashes, verbose=verbose)
    if len(changed) == 0 and len(deleted) == 0:
        # If there is no change do not create a patch.
        # Would be a waste of time...
        return None, [], should_be
    with open(os.path.join(folder, ".md5.json"), "w") as f:
        f.write(json.dumps(should_be))
    changed.append(".md5.json")
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H.%M.%S')
    patch_name = timestamp  + "_" + folder.replace("\\", "/").split("/")[-1] + ".zip"
    if verbose:
        print("Compressing patch in {}".format(patch_name))
    with zipfile.ZipFile(patch_name, 'w', zipfile.ZIP_DEFLATED) as ziph:
        for file in changed:
            if verbose:
                print(os.path.join(folder, file).replace(os.sep, "/"))
            ziph.write(os.path.join(".", file).replace(os.sep, "/"))
    if verbose:
        print("Packed patch in {}".format(patch_name))
    os.remove(os.path.join(folder, ".md5.json"))
    return patch_name, deleted, should_be


def apply_patch(name, target):
    with zipfile.ZipFile(name + '.zip', 'r') as zip_ref:
        zip_ref.extractall(target)

    # remove emtpy dirs
    empty_dirs = __get_empty_folders(target, [])
    for d in empty_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)


def test_diff():
    server_hashes = get_files_hash_map(".", [])
    server_hashes["requirements.txt"] = "asdjwoegjowjf"
    server_hashes["foobar.txt"] = "siudgusejfroj"
    del server_hashes["README.md"]
    patch_name, deleted, hashes = pack_patch("/home/fuerst/Git/rempy", server_hashes, verbose=True)
    print(f"Patch file: {patch_name}")
    print(f"Deleted: {deleted}")
    #apply_patch(patch_name, ".")
    os.remove(patch_name)
    print("Test: Successfull")


def test_diff_no_patch():
    server_hashes = get_files_hash_map(".", [])
    patch_name, deleted, hashes = pack_patch("/home/fuerst/Git/rempy", server_hashes, verbose=True)
    print(f"Patch file: {patch_name}")
    print(f"Deleted: {deleted}")
    #apply_patch(patch_name, ".")
    if patch_name is not None:
        os.remove(patch_name)
    else:
        print("Test: Successfull")


if __name__ == "__main__":
    print("# Test fake changes and patch packing.")
    test_diff()
    print()
    print("# Test no changes.")
    test_diff_no_patch()

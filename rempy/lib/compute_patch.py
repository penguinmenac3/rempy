import os
import shutil
import hashlib
import zipfile
import time
import datetime

PYTHON_IGNORE_LIST = ["__pycache__", "*.pyc"]

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
    res = candidate in forbidden_list
    for item in start_list:
        res |= candidate.startswith(item)
    for item in end_list:
        res |= candidate.endswith(item)
    return res

def __get_all_files(root, forbidden_list=PYTHON_IGNORE_LIST):
    all_files = []
    root_with_sep = root + os.sep
    for path, subdirs, files in os.walk(root):
        files = [x for x in files if not __ignore(x, forbidden_list)]
        subdirs[:] = [x for x in subdirs if not x.startswith(".") and not __ignore(x, forbidden_list)]
        for name in files:
            all_files.append(os.path.join(path, name).replace(root_with_sep, ""))
    return all_files


def __get_empty_folders(root, forbidden_list=PYTHON_IGNORE_LIST):
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

def get_files_hash_map(root, forbidden_list=PYTHON_IGNORE_LIST):
    files = __get_all_files(root, forbidden_list)
    md5s = [__md5(os.path.join(root, f)) for f in files]
    hash_map = dict(zip(files, md5s))
    return hash_map

def pack_patch(folder, server_hashes, verbose=False):
    should_be = get_files_hash_map(folder)
    changed, deleted = __diff(should_be, server_hashes, verbose=verbose)
    timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H.%M.%S')
    patch_name = timestamp  + "_" + folder.replace("\\", "/").split("/")[-1] + ".zip"
    if verbose:
        print("Compressing patch in {}".format(patch_name))
    with zipfile.ZipFile(patch_name, 'w', zipfile.ZIP_DEFLATED) as ziph:
        for file in changed:
            if verbose:
                print(os.path.join(folder, file))
            ziph.write(os.path.join(".", file))
    if verbose:
        print("Packed patch in {}".format(patch_name))
    return patch_name, deleted


def apply_patch(name, target):
    with zipfile.ZipFile(name + '.zip', 'r') as zip_ref:
        zip_ref.extractall(target)

    # remove emtpy dirs
    empty_dirs = __get_empty_folders(target)
    for d in empty_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)

def test_diff():
    server_hashes = get_files_hash_map(".")
    server_hashes["requirements.txt"] = "asdjwoegjowjf"
    server_hashes["foobar.txt"] = "siudgusejfroj"
    del server_hashes["README.md"]
    patch_name, deleted = pack_patch("/home/fuerst/Git/rempy", server_hashes, verbose=True)
    print(deleted)
    #apply_patch(patch_name, ".")
    os.remove(patch_name)
    print("Test: Successfull")


if __name__ == "__main__":
    test_diff()

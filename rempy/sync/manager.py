"""doc
# sync_files.py

> Implements synchronization of files on local and remote system.

License: MIT (see main license)
Authors:
* Michael Fuerst (Lead)
"""
import os
import json
import time
from json.decoder import JSONDecodeError

from rempy.sync.patcher import pack_patch


class SyncManager(object):
    def __init__(self, host, user, local_workdir, remote_workdir):
        self._conn = None
        self._host = host
        self._user = user
        self._local_workdir = local_workdir
        self._remote_workdir = remote_workdir

    def _run(self, cmd):
        print(f"> {cmd}")
        os.system(cmd)
    
    def _get_remote_hashes(self):
        local_hash_path = os.path.join(self._local_workdir, ".md5.json")
        self._run(f"scp {self._user}@{self._host}:{self._remote_workdir}/.md5.json {local_hash_path}")
        data = ""
        if os.path.exists(local_hash_path):
            with open(local_hash_path, "r") as f:
                data = f.read()
            os.remove(local_hash_path)
            try:
                return json.loads(data)
            except JSONDecodeError:
                pass
        print(f"No valid json from server: {data}")
        return {}

    def sync(self, hashes=None):
        if hashes is None:
            hashes = self._get_remote_hashes()
        patch_path, deleted, hashes = pack_patch(self._local_workdir, hashes)
        if patch_path is not None:
            self._run(f"scp {patch_path} {self._user}@{self._host}:{self._remote_workdir}/patch.zip")
            self._run(f"ssh {self._user}@{self._host} \"cd {self._remote_workdir} && unzip -o patch.zip && rm patch.zip\"")
            self._run(f"rm {patch_path}")
            if len(deleted) > 0:
                deleted = " ".join(deleted)
                self._run(f"ssh {self._user}@{self._host} \"cd {self._remote_workdir} && rm -rf {deleted}\"")
        return hashes

    def watch(self, check_interval):
        old_hashes = self.sync()
        while True:
            time.sleep(check_interval)
            old_hashes = self.sync(hashes=old_hashes)

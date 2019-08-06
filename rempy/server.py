import entangle
import base64
import os
import shutil
import sys
from time import sleep, time, strftime, gmtime
from threading import Thread, Condition
from functools import partial
import subprocess
import signal
import json

from rempy.lib.compute_patch import get_files_hash_map, apply_patch
from rempy.lib.console_buffer import ConsoleBuffer, ConsoleState


CONFIG_PATH = os.path.join(os.environ["userprofile"] if os.name == "nt" else os.environ["HOME"], ".rempy-server.json")


def config():
    conf = {
        "host": "*",
        "port": 24454,
        "users": {
            "deepthought": "42"
        },
        "gpus": [0]
    }
    with open(CONFIG_PATH, "w") as f:
        f.write(json.dumps(conf, indent=4, sort_keys=True))
    print("Created basic config at {}. You should change at least the password!".format(CONFIG_PATH))


class Server(object):
    def __init__(self, conf=None):
        if conf is None:
            if not os.path.exists(CONFIG_PATH):
                raise RuntimeError("You must create a config first via 'rempy config-server'.")
            with open(CONFIG_PATH, "r") as f:
                conf = json.loads(f.read())
        rempy_home = "/tmp/rempy"
        if os.name == "nt":
            rempy_home = os.path.join(os.environ["TEMP"], "rempy")
        if "REMPY_HOME" in os.environ:
            rempy_home = os.environ["REMPY_HOME"]
        print("REMPY_HOME={}".format(rempy_home))
        os.environ["REMPY_HOME"] = rempy_home

        self.conf = conf
        self.processes = {}
        self.results = {}
        self.__condition = Condition()
        self.__condition_gpu_assignment = Condition()
        self.proc_id = 0
        self.gpus = []
        if "gpus" in conf:
            self.gpus = conf["gpus"]
        self.assigned_gpus = []

    def is_free(self, gpu):
        if gpu in self.assigned_gpus:
            return False

        # TODO check if gpu is occupied by foreign process.

        return True

    def _get_free_gpu(self):
        for x in self.gpus:
            if self.is_free(x):
                return x
        return None

    def await_gpu(self):
        gpu = self._get_free_gpu()
        while gpu is None:
            self.__condition_gpu_assignment.acquire()
            self.__condition_gpu_assignment.wait()
            self.__condition_gpu_assignment.release()
            gpu = self._get_free_gpu()
        assert gpu is not None

        self.assigned_gpus.append(gpu)
        return gpu

    def free_gpu(self, gpu):
        self.assigned_gpus.remove(gpu)
        self.__condition_gpu_assignment.acquire()
        self.__condition_gpu_assignment.notify_all()
        self.__condition_gpu_assignment.release()

    def pollPipe(self, pname):
        while pname in self.processes:
            line = self.processes[pname].stdout.read(1).decode("utf-8")
            if line != '':
                # the real code does filtering here
                self.results[pname].append(line)
                self.__condition.acquire()
                self.__condition.notify_all()
                self.__condition.release()
            else:
                break
        del self.processes[pname]
        self.__condition.acquire()
        self.__condition.notify_all()
        self.__condition.release()
        print("Finished Process: {}".format(pname))

    def callback(self, entanglement):
        gpu = None
        local_result = ConsoleState()
        project_name = entanglement.get("rempy_project_name")
        project_path = os.path.join(os.environ["REMPY_HOME"], project_name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        env = entanglement.get("rempy_env")
        rprint = entanglement.remote_fun("rempy_print")
        pname = env["reconnect"]

        if not pname:
            hash_map = get_files_hash_map(project_path, forbidden_list=[])
            entanglement.rempy_hash_map = hash_map

            # Wait for patch and to delete
            patch_file_content, deleted = entanglement.get("rempy_patch")

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
            command = entanglement.get("rempy_command")

            # Start program
            env["reconnect"] = "{}.{}".format(self.proc_id, env["name"])
            pname = env["reconnect"]
            self.proc_id += 1
            rprint("pname: {}".format(env["reconnect"]))
            rprint()

            preex = None
            try:
                preex = os.setsid
            except AttributeError:
                print("Windows: Feature not availible.")
            osenv = os.environ.copy()
            osenv["PYTHONUNBUFFERED"] = "True"
            osenv["NAME"] = env["name"]
            if "gpu" in env:
                if env["gpu"] == "schedule":
                    gpu = self.await_gpu()
                else:
                    gpu = env["gpu"]
                osenv["CUDA_VISIBLE_DEVICES"] = str(gpu)
            self.processes[pname] = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=False, preexec_fn=preex,
                env=osenv, bufsize=1, cwd=project_path)
            print("Started Process: {}".format(pname))
            self.results[pname] = ConsoleBuffer()
            Thread(target=self.pollPipe, args=(pname,)).start()
        else:
            if pname not in self.results:
                res = None
                for k in self.results.keys():
                    tmp = ".".join(k.split(".")[1:])
                    if tmp == pname:
                        res = k
                if res is None:
                    rprint("Unknown process pick one: {}".format(list(self.results.keys())))
                    entanglement.close()
                    return
                pname = res

        entanglement.rempy_pname = pname
        if env["kill"]:
            self.processes[pname].kill()
            print("Killed Process: {}".format(pname))

        # Forward outputs/inputs to network
        while pname in self.results:
            update = self.results[pname].get_update(local_result)
            rprint(update, end="")
            if pname not in self.processes:
                break
            self.__condition.acquire()
            self.__condition.wait()
            self.__condition.release()

        # Close connection
        entanglement.close()


def main():
    server = Server()
    host = server.conf["host"]
    port = server.conf["port"]
    users = server.conf["users"]
    # Start a listener for connections
    entangle.listen(host=host, port=port, users=users, callback=server.callback)

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


CONFIG_PATH = os.path.join(os.environ["userprofile"] if os.name == "nt" else os.environ["HOME"], ".rempy-server.json")


def config():
    conf = {
        "host": "*",
        "port": 24454,
        "password": "42"
    }
    with open(CONFIG_PATH, "w") as f:
        f.write(json.dumps(conf, indent=4, sort_keys=True))
    print("Created basic config at {}. You should change at least the password!".format(CONFIG_PATH))


class Server(object):
    def __init__(self):
        self.processes = {}
        self.results = {}
        self.__condition = Condition()
        self.proc_id = 0

    def pollPipe(self, pname):
        while pname in self.processes:
            line = self.processes[pname].stdout.read(1).decode("utf-8")
            if line != '':
                #the real code does filtering here
                self.results[pname] = self.results[pname] + line
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

    def run(self, entanglement):
        local_result = 0
        project_name = entanglement.get("project_name")
        project_path = os.path.join(os.environ["REMPY_HOME"], project_name)
        if not os.path.exists(project_path):
            os.makedirs(project_path)
        env = entanglement.get("env")
        rprint = entanglement.remote_fun("print")
        pname = env["reconnect"]
        
        if not pname:
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
            self.processes[pname] = subprocess.Popen(
                command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=False, preexec_fn=preex,
                env=osenv, bufsize=1, cwd=project_path)
            print("Started Process: {}".format(pname))
            self.results[pname] = ""
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

        entanglement.pname = pname
        if env["kill"]:
            self.processes[pname].kill()
            print("Killed Process: {}".format(pname))

        # Forward outputs/inputs to network
        while pname in self.results:
            tmp = self.results[pname][local_result:]
            local_result = len(self.results[pname])
            rprint(tmp, end="")
            if pname not in self.processes:
                break
            self.__condition.acquire()
            self.__condition.wait()
            self.__condition.release()

        # Close connection
        entanglement.close()

def main():
    if not os.path.exists(CONFIG_PATH):
        print("You must create a config first via 'rempy config-server'.")
        return
    with open(CONFIG_PATH, "r") as f:
        conf = json.loads(f.read())
    rempy_home = "/tmp/rempy"
    if os.name == "nt":
        rempy_home = os.path.join(os.environ["TEMP"], "rempy")
    if "REMPY_HOME" in os.environ:
        rempy_home = os.environ["REMPY_HOME"]
    print("REMPY_HOME={}".format(rempy_home))
    os.environ["REMPY_HOME"] = rempy_home

    server = Server()
    host = conf["host"]
    port = conf["port"]
    password = conf["password"]
    
    # Start a listener for connections
    entangle.listen(host=host, port=port, password=password, callback=server.run)

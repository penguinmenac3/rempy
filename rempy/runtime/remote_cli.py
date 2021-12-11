"""doc
# connection.py

> Implements a connection to a remote machine via which file transfers and commands can be done.

License: MIT (see main license)
Authors:
* Michael Fuerst (Lead)
"""
import sys
import uuid

try:
    from pexpect import spawn as pexpect_spawn
except ImportError:
    from pexpect.popen_spawn import PopenSpawn

    class pexpect_spawn(PopenSpawn):
        def isalive(self):
            return self.proc.poll() is None


class RemoteCLI(object):
    def __init__(self, host, user, remote_workdir, interface="ssh", interface_args=""):
        self._uuid = uuid.UUID()
        self._conn = None
        self._original_host = host
        self._host = host
        self._user = user
        self._remote_workdir = remote_workdir
        self._interface = interface
        self._interface_args = interface_args

        if self._interface == "ssh":
            self._connect_ssh()
        elif self._interface == "slurm":
            self._connect_ssh()
            self._connect_slurm()
        else:
            raise NotImplementedError(f"No interface '{interface}' implemented.")
        self._setup_env()

    def _setup_env(self):
        self.run(f"screen -S {self._uuid}")
        self.expect_prompt()
        print(f"### Screen name: {self._uuid} ###")
        self.run(f"cd {self._remote_workdir}")
        self.expect_prompt()

    def _connect_ssh(self):
        print("Connecting via SSH.")
        self.run(f"ssh -o StrictHostKeyChecking=no {self._user}@{self._host}")
        self.expect_prompt()

    def _connect_slurm(self):
        print("Connecting via SLURM (interactive)")
        self.run(f"srun {self._interface_args} -v --pty bash -i" "")
        self._host = self.expect("srun: Node (.*), .* tasks started")[0]
        self.expect_prompt()

    def expect(self, regex, has_return=True):
        if self._conn is None:
            raise RuntimeError("No connection available. Something broke in the init.")
        self._conn.expect(regex)
        if has_return:
            return self._conn.match.groups()

    def expect_prompt(self):
        self.expect("\n.*@.*:.*")

    def run(self, command, timeout=600):
        print(f"> {command}")
        if self._conn is None:
            self._conn = pexpect_spawn(command, timeout=timeout, logfile=sys.stdout)
        else:
            self._conn.sendline(command)

    def execute_script(self, script, launcher, debug):
        debug_prefix = ""
        if debug:
            # TODO populate debug prefix for debugging.
            print("TODO populate debug prefix for debugging.")
        command = f"{debug_prefix}{launcher} {script}"
        self.run(command)
        self.run("exit")
        self.expect("exit")
        if debug:
            self.tunnel_debugger()
        self.join()

    def tunnel_debugger(self):
        # TODO open SSH tunnel for debug ports.
        print("TODO open SSH tunnel for debug ports.")

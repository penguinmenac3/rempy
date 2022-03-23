"""doc
# connection.py

> Implements a connection to a remote machine via which file transfers and commands can be done.

License: MIT (see main license)
Authors:
* Michael Fuerst (Lead)
"""
from uuid import uuid4
from pexpect import spawn as pexpect_spawn
import re
def escape_ansi(line):
    ansi_escape =re.compile(r'(\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]')
    return ansi_escape.sub('', line)


class CustomLogger(object):
    def __init__(self) -> None:
        self.output = False
        self.command = ""
    
    def current_command(self, command):
        print(f"> {command}")
        self.command = command

    def write(self, data):
        try:
            data = data.decode("utf-8")
            data = escape_ansi(data)
        except:
            pass
        if self.output:
            try:
                if self.command not in data:
                    print(data, end="")
            except Exception as e:
                print("REMPY EXCEPTION", e)
    
    def flush(self):
        pass


def _run(command, conn, logger):
    logger.current_command(command)
    if conn is None:
        conn = pexpect_spawn(command, timeout=None, logfile=logger)
    else:
        conn.sendline(command)
    return conn


def remoteExecute(host, user, remote_workdir, script, args, launcher, debug=0, interface="ssh", ssh_args="", slurm_args="", pre_launch="", logfile=None):
    # Initialize variables with defaults
    _conn = None
    _debug_conn = None
    uuid = ""
    debug_prefix = ""
    logger = CustomLogger()
    debug_conn_logger = CustomLogger()

    # Validate arguments
    if interface not in ["slurm", "ssh", "local"]:
        raise NotImplementedError(f"No interface '{interface}' implemented.")

    # Build command
    if debug > 0 and launcher.startswith("python"):
        debug_prefix = f"python -m debugpy --listen localhost:{debug} --wait-for-client "
        launcher = launcher.replace("python", "")
    if pre_launch != "":
        pre_launch = f"cd {remote_workdir} && {pre_launch} && "
    command = f"{pre_launch}cd {remote_workdir} && {debug_prefix}{launcher} {script} {args}"
    if logfile is not None:
        command = f"echo > {logfile} && {command} 2>&1 | tee {logfile}"
    command = f"bash -c '{command}'"
    if interface in ["slurm"]:
        command = f"srun {slurm_args} -v {command}"
    if interface in ["ssh", "slurm"]:
        uuid = str(uuid4())
        if host != "localhost":
            _conn = _run(f"ssh {ssh_args} {user}@{host}", _conn, logger)
            _conn.expect("\n.*@.*:.*")
        command = f"screen -S {uuid} {command}"

    logger.output = True
    _conn = _run(command, _conn, logger)
    if interface in ["slurm"]:
        _conn.expect("srun: Node (.*), .* tasks started")
        node = _conn.match.groups()[0].decode("utf-8")
        if debug > 0:
            inner_forward = f"ssh -o StrictHostKeyChecking=no -N -L {debug}:localhost:{debug} {node}"
            if host != "localhost":
                # Forward port again if not on localhost.
                _debug_conn = _run(f"ssh {ssh_args} -L {debug}:localhost:{debug} {user}@{host} {inner_forward}", _debug_conn, debug_conn_logger)
            else:
                # Only use inner forward if on slurm head node.
                _debug_conn = _run(inner_forward)
    if interface in ["ssh"] and debug:
        # Forward port if not on localhost.
        if debug > 0 and host != "localhost":
            _debug_conn = _run(f"ssh {ssh_args} -N -L {debug}:localhost:{debug} {user}@{host}", _debug_conn, debug_conn_logger)

    try:
        if uuid != "":
            _conn.expect("screen is terminating")
            logger.output = False
            _conn = _run("exit", _conn, logger)
            _conn.expect("exit")
        else:
            while _conn.isalive():
                _conn.read()
    except KeyboardInterrupt:
        _conn.kill()

    if _debug_conn is not None:
        _debug_conn.kill(9)

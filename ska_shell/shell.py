# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Utilities to run subprocesses"""

import datetime
import functools
import logging
import re
import os
import sys
import signal
import subprocess


class ShellError(Exception):
    pass


class NonZeroReturnCode(ShellError):
    pass


def _fix_paths(
    envs,
    pathvars=(
        "PATH",
        "PERLLIB",
        "PERL5LIB",
        "PYTHONPATH",
        "LD_LIBRARY_PATH",
        "MANPATH",
        "INFOPATH",
    ),
):
    """For the specified env vars that represent a search path, make sure that the
    paths are unique.  This allows the environment setting script to be lazy
    and not worry about it.  This routine gives the right-most path precedence
    and modifies C{envs} in place.

    :param envs: Dict of environment vars
    :param pathvars: List of path vars that will be fixed
    :rtype: None (envs is modified in-place)
    """

    # Process env vars that are contained in the PATH_ENVS set
    for key in set(envs.keys()) & set(pathvars):
        path_ins = envs[key].split(":")
        pathset = set()
        path_outs = []
        # Working from right to left add each path that hasn't been included yet.
        for path in reversed(path_ins):
            if path not in pathset:
                pathset.add(path)
                path_outs.append(path)
        envs[key] = ":".join(reversed(path_outs))


def _parse_keyvals(keyvals):
    """Parse the key=val pairs from the newline-separated string.

    :param keyvals: Newline-separated string with key=val pairs
    :rtype: Dict of key=val pairs.
    """
    re_keyval = re.compile(r"([\w_]+) \s* = \s* (.*)", re.VERBOSE)
    keyvalout = {}
    for keyval in keyvals:
        m = re.match(re_keyval, keyval)
        if m:
            key, val = m.groups()
            keyvalout[key] = val
    return keyvalout


def communicate(process, logfile=None, logger=None, log_level=None):
    """
    Real-time reading of a subprocess stdout.

    Parameters
    ----------
    :param process: process returned by subprocess.Popen
    :param logfile: append output to the suppplied file object
    :param logger: log output to the supplied logging.Logger
    :param log_level: log level for logger
    """
    log_level = "INFO" if log_level is None else log_level
    log_level = getattr(logging, log_level) if type(log_level) is str else log_level

    lines = []
    while True:
        if process.poll() is not None:
            break
        line = process.stdout.readline()
        line = line.decode() if isinstance(line, bytes) else line
        if line:
            if logfile:
                logfile.write(line)
            if logger is not None:
                logger.log(log_level, line[:-1])
            lines.append(line[:-1])

    # in case the buffer is still not empty after the process ended
    for line in process.stdout.readlines():
        line = line.decode() if isinstance(line, bytes) else line
        if line:
            if logfile:
                logfile.write(line)
            if logger is not None:
                logger.log(log_level, line[:-1])
            lines.append(line[:-1])

    return lines


@functools.cache
def _shell_ok(shell):
    p = subprocess.run(["which", shell], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.returncode == 0


def run_shell(
    cmdstr,
    shell="bash",
    logfile=None,
    importenv=False,
    getenv=False,
    env=None,
    logger=None,
    log_level=None,
    check=None,
):
    """
    Run the command string ``cmdstr`` in a ``shell`` ('bash' or 'tcsh').  It can have
    multiple lines.  Each line is separately sent to the shell.  The exit status is
    checked if the shell comes back with a prompt. If exit status is non-zero at any point
    then processing is terminated and a ``ShellError`` exception is raise.

    :param cmdstr: command string
    :param shell: shell for command -- 'bash' (default) or 'tcsh'
    :param logfile: append output to the suppplied file object
    :param importenv: import any environent changes back to python env
    :param getenv: get the environent changes after running ``cmdstr``
    :param env: set environment using ``env`` dict prior to running commands
    :param check: raise an exception if any command fails

    :rtype: (outlines, deltaenv)
    """
    check = check if check is not None else True

    environ = dict(os.environ)
    if env is not None:
        environ.update(env)

    if not _shell_ok(shell):
        raise Exception(f'Failed to find "{shell}" shell')

    if importenv or getenv:
        cmdstr += " && echo __PRINTENV__ && printenv"

    # all lines are joined so the shell exits at the first failure
    cmdstr = " && ".join([c for c in cmdstr.splitlines() if c.strip()])

    # make sure the RC file is not sourced in csh (option -f) and abort on error (option -e)
    actual_shell = shell
    actual_cmdstr = cmdstr
    if shell in ["tcsh", "csh"]:
        actual_cmdstr = f"{shell} {'-e' if check else ''} -f -c '{actual_cmdstr}'"
        actual_shell = "bash"
    elif shell in ["bash", "zsh"] and check:
        actual_cmdstr = f"set -e; {actual_cmdstr}"

    proc = subprocess.Popen(
        [actual_cmdstr],
        executable=actual_shell,
        shell=True,
        env=environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if logfile:
        time = datetime.datetime.now().isoformat()[:22]
        logfile.write(f"{shell.capitalize()}-{time}> {cmdstr}\n")
    stdout = communicate(proc, logfile=logfile, logger=logger, log_level=log_level)
    if logfile:
        time = datetime.datetime.now().isoformat()[:22]
        logfile.write(f"{shell.capitalize()}-{time}>\n")
    if check and proc.returncode:
        msg = " ".join(stdout[-1:])  # stdout could be empty
        exc = NonZeroReturnCode(f"Shell error: {msg}")
        exc.lines = stdout
        raise exc

    newenv = {}
    if "__PRINTENV__" in stdout:
        newenv = _parse_keyvals(stdout[stdout.index("__PRINTENV__") + 1 :])
        stdout = stdout[: stdout.index("__PRINTENV__")]

    # Update os.environ based on changes to environment made by cmdstr
    deltaenv = dict()
    if importenv or getenv:
        expected_diff_set = (
            set(("PS1", "PS2", "_", "SHLVL")) if actual_shell in ["bash", "zsh"] else set()
        )
        currenv = dict(os.environ)
        _fix_paths(newenv)
        for key in set(newenv) - expected_diff_set:
            if key not in currenv or currenv[key] != newenv[key]:
                deltaenv[key] = newenv[key]
        if importenv:
            os.environ.update(deltaenv)

    return stdout, deltaenv


def bash_shell(
    cmdstr,
    logfile=None,
    importenv=False,
    getenv=False,
    env=None,
    logger=None,
    log_level=None,
    check=None
):
    """
    Run the command string ``cmdstr`` in a bash shell.  It can have
    multiple lines. If exit status is non-zero at any point
    then processing is terminated and a ``ShellError`` exception is raised.

    :param cmdstr: command string
    :param shell: shell for command -- 'bash' (default) or 'tcsh'
    :param logfile: append output to the suppplied file object
    :param importenv: import any environent changes back to python env
    :param getenv: get the environent changes after running ``cmdstr``
    :param env: set environment using ``env`` dict prior to running commands
    :param logger: log output to the supplied logging.Logger
    :param log_level: log level for logger

    :rtype: (outlines, deltaenv)
    """
    outlines, newenv = run_shell(
        cmdstr,
        shell="bash",
        logfile=logfile,
        importenv=importenv,
        getenv=getenv,
        env=env,
        logger=logger,
        log_level=log_level,
        check=check,
    )
    return outlines, newenv


def bash(cmdstr, logfile=None, importenv=False, env=None, logger=None, log_level=None, check=None):
    """Run the ``cmdstr`` string in a bash shell.  See ``run_shell`` for options.

    :returns: bash output
    """
    return run_shell(
        cmdstr,
        shell="bash",
        logfile=logfile,
        importenv=importenv,
        env=env,
        logger=logger,
        log_level=log_level,
        check=check,
    )[0]


def tcsh(cmdstr, logfile=None, importenv=False, env=None, logger=None, log_level=None, check=None):
    """Run the ``cmdstr`` string in a tcsh shell.  See ``run_shell`` for options.

    :returns: tcsh output
    """
    return run_shell(
        cmdstr,
        shell="tcsh",
        logfile=logfile,
        importenv=importenv,
        env=env,
        logger=logger,
        log_level=log_level,
        check=check,
    )[0]


def tcsh_shell(
    cmdstr,
    logfile=None,
    importenv=False,
    getenv=False,
    env=None,
    logger=None,
    log_level=None,
    check=None,
):
    """
    Run the command string ``cmdstr`` in a tcsh shell.  It can have
    multiple lines. If exit status is non-zero at any point
    then processing is terminated and a ``ShellError`` exception is raised.

    :param cmdstr: command string
    :param shell: shell for command -- 'bash' (default) or 'tcsh'
    :param logfile: append output to the suppplied file object
    :param importenv: import any environent changes back to python env
    :param getenv: get the environent changes after running ``cmdstr``
    :param env: set environment using ``env`` dict prior to running commands
    :param logger: log output to the supplied logging.Logger
    :param log_level: log level for logger

    :rtype: (outlines, deltaenv)
    """
    outlines, newenv = run_shell(
        cmdstr,
        shell="tcsh",
        logfile=logfile,
        importenv=importenv,
        getenv=getenv,
        env=env,
        logger=logger,
        log_level=log_level,
        check=check,
    )
    return outlines, newenv


def getenv(cmdstr, shell="bash", importenv=False, env=None):
    """Run the ``cmdstr`` string in ``shell``.  See ``run_shell`` for options.

    :returns: Dict of environment vars update produced by ``cmdstr``
    """

    _, newenv = run_shell(
        cmdstr, shell=shell, importenv=importenv, env=env, getenv=True, check=False
    )
    return newenv


def importenv(cmdstr, shell="bash", env=None):
    """Run ``cmdstr`` in a bash shell and import the environment updates into the
    current python environment (os.environ).  See ``bash_shell`` for options.

    :returns: Dict of environment vars update produced by ``cmdstr``
    """
    return getenv(cmdstr, importenv=True, env=env, shell=shell)


# Null file-like object.  Needed because pyfits spews warnings to stdout


class _NullFile:
    def write(self, data):
        pass

    def writelines(self, lines):
        pass

    def flush(self):
        pass

    def close(self):
        pass


class RunTimeoutError(RuntimeError):
    pass


class Spawn(object):
    """
    Provide methods to run subprocesses in a controlled and simple way.  Features:
     - Uses the subprocess.Popen() class
     - Send stdout and/or stderr output to a file
     - Specify a job timeout
     - Catch exceptions and log warnings

    Example usage:

      >>> from ska_shell import Spawn, bash, getenv, importenv
      >>>
      >>> spawn = Spawn()
      >>> status = spawn.run(['echo', 'hello'])
      hello
      >>> status
      0
      >>>
      >>> try:
      ...     spawn.run(['bad', 'command'])
      ... except Exception, error:
      ...     error
      ...
      OSError(2, 'No such file or directory')
      >>> spawn.run(['bad', 'command'], catch=True)
      Warning - OSError: [Errno 2] No such file or directory
      >>> print spawn.exitstatus
      None
      >>> print spawn.outlines
      ['Warning - OSError: [Errno 2] No such file or directory\\n']
      >>>
      >>> spawn = Spawn(stdout=None, shell=True)
      >>> spawn.run('echo hello')
      0
      >>> spawn.run('fail fail fail')
      127
      >>>
      >>> spawn = Spawn(stdout=None, shell=True, stderr=None)
      >>> spawn.run('fail fail fail')
      127
      >>> print spawn.outlines
      []

    Additional object attributes:
     - openfiles: List of file objects created during init corresponding
                  to filenames supplied in ``outputs`` list
    """

    def _open_for_write(self, f):
        """Return a file object for writing for ``f``, which may be nothing, a file
        name, or a file-like object."""
        if not f:
            return _NullFile()
        # Else see if it is a single file-like object
        elif hasattr(f, "write") and hasattr(f, "close"):
            return f
        else:
            openfile = open(f, "w", 1)  # raises TypeError if f is not suitable
            self.openfiles.append(
                openfile
            )  # Store open file objects created by this object
            return openfile

    @staticmethod
    def _timeout_handler(pid, timeout):
        def handler(signum, frame):
            raise RunTimeoutError(
                "Process pid=%d timed out after %d secs" % (pid, timeout)
            )

        return handler

    def __init__(
        self,
        stdout=sys.stdout,
        timeout=None,
        catch=False,
        stderr=subprocess.STDOUT,
        shell=False,
    ):
        """Create a Spawn object to run shell processes in a controlled way.

        :param stdout: destination(s) for process stdout.  Can be None, a file name,
             a file object, or a list of these.
        :param timeout: command timeout (default: no timeout)
        :param catch: catch exceptions and just log a warning message
        :param stderr: destination for process stderr.  Can be None, a file object,
             or subprocess.STDOUT (default).  The latter merges stderr into stdout.
        :param shell: send run() cmd to shell (subprocess Popen shell parameter)

        :rtype: Spawn object
        """
        self.stdout = stdout
        self.timeout = timeout or 0
        self.catch = catch
        self.stderr = stderr
        self.shell = shell
        self.openfiles = []  # Newly opened file objects for stdout

        # stdout can be None, <file>, 'filename', or sequence(..) of these
        try:
            self.outfiles = [self._open_for_write(self.stdout)]
        except TypeError:
            self.outfiles = [self._open_for_write(f) for f in self.stdout]

    def _write(self, line):
        for f in self.outfiles:
            f.write(line)
        self.outlines.append(line)

    def run(self, cmd, timeout=None, catch=None, shell=None):
        """Run the command ``cmd`` and abort if timeout is exceeded.

        Attributes after run():
         - outlines: list of output lines from process
         - exitstatus: process exit status or None if an exception occurred

        :param cmd: list of strings or a string(see Popen docs)
        :param timeout: command timeout (default: ``self.timeout``)
        :param catch: catch exceptions (default: ``self.catch``)
        :param shell: run cmd in shell (default: ``self.shell``)

        :rtype: process exit value
        """

        # Use object defaults if params not supplied
        if timeout is None:
            timeout = self.timeout
        if catch is None:
            catch = self.catch
        if shell is None:
            shell = self.shell

        # stderr = None is taken to imply catching stderr, done with PIPE
        stderr = self.stderr or subprocess.PIPE

        self.outlines = []
        self.exitstatus = None

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=stderr,
                shell=shell,
                universal_newlines=True,
            )

            prev_alarm_handler = signal.signal(
                signal.SIGALRM, Spawn._timeout_handler(self.process.pid, timeout)
            )
            signal.alarm(self.timeout)
            for line in self.process.stdout:
                self._write(line)
            self.exitstatus = self.process.wait()
            signal.alarm(0)

            signal.signal(signal.SIGALRM, prev_alarm_handler)

        except RunTimeoutError as e:
            if catch:
                self._write("Warning - RunTimeoutError: %s\n" % e)
            else:
                raise

        except OSError as e:
            if catch:
                self._write("Warning - OSError: %s\n" % e)
            else:
                raise

        return self.exitstatus

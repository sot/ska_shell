import os
import unittest
from StringIO import StringIO
from Ska.Shell import Spawn, RunTimeoutError, bash, tcsh, getenv, importenv

outfile = 'ska_shell_test.dat'


class TestSpawn(unittest.TestCase):
    def setUp(self):
        self.f = StringIO()
        self.g = StringIO()

    def test_ok(self):
        spawn = Spawn(stdout=self.f)
        spawn.run(['echo', 'hello world'])
        self.assertEqual(spawn.exitstatus, 0)
        self.assertEqual(spawn.outlines, ['hello world\n'])
        self.assertEqual(self.f.getvalue(), 'hello world\n')

    def test_os_error(self):
        spawn = Spawn(stdout=None)
        self.assertRaises(OSError, spawn.run, 'bad command')
        self.assertEqual(spawn.exitstatus, None)

    def test_timeout_error(self):
        spawn = Spawn(shell=True, timeout=1, stdout=None)
        self.assertRaises(RunTimeoutError, spawn.run, 'sleep 5')
        self.assertEqual(spawn.exitstatus, None)

    def test_grab_stderr(self):
        f = open(outfile, 'w')
        spawn = Spawn(stderr=f, stdout=None)
        spawn.run('perl -e "print STDERR 123456"', shell=True)
        f.close()
        f = open(outfile)
        self.assertEqual(f.read(), '123456')
        self.assertEqual(spawn.exitstatus, 0)
        os.unlink(outfile)

    def test_multi_stdout(self):
        spawn = Spawn(stdout=[self.f, self.g])
        spawn.run('perl -e "print 123456"', shell=True)
        self.assertEqual(self.f.getvalue(), '123456')
        self.assertEqual(self.g.getvalue(), '123456')
        self.assertEqual(spawn.exitstatus, 0)

    def test_shell_error(self):
        # With shell=True you don't get an OSError
        spawn = Spawn(shell=True, stdout=None)
        spawn.run('sadfasdfasdf')
        self.assertNotEqual(spawn.exitstatus, 0)
        self.assertNotEqual(spawn.exitstatus, None)


class TestBash:
    def test_bash(self):
        outlines = bash('echo line1; echo line2')
        assert outlines == ['line1', 'line2']

    def test_env(self):
        envs = getenv('export TEST_ENV_VAR="hello"')
        assert envs['TEST_ENV_VAR'] == 'hello'
        outlines = bash('echo $TEST_ENV_VAR', env=envs)
        assert outlines == ['hello']

    def test_importenv(self):
        importenv('export TEST_ENV_VAR="hello"', env={'TEST_ENV_VAR2': 'world'})
        assert os.environ['TEST_ENV_VAR'] == 'hello'
        assert os.environ['TEST_ENV_VAR2'] == 'world'

    def test_logfile(self, tmpdir):
        logfile = StringIO()
        bash('echo line1; echo line2', logfile=logfile)
        logfile.seek(0)
        outlines = logfile.read().splitlines()
        assert outlines[0].startswith('Bash-')
        assert outlines[1] == 'line1'
        assert outlines[2] == 'line2'
        assert outlines[3].startswith('Bash')


class TestTcsh:
    def test_tcsh(self):
        outlines = tcsh('echo line1; echo line2')
        assert outlines == ['line1', 'line2']

    def test_env(self):
        envs = getenv('setenv TEST_ENV_VAR2 "hello"', shell='tcsh')
        assert envs['TEST_ENV_VAR2'] == 'hello'
        outlines = tcsh('echo $TEST_ENV_VAR2', env=envs)
        assert outlines == ['hello']

    def test_importenv(self):
        importenv('setenv TEST_ENV_VAR3 "hello"', env={'TEST_ENV_VAR4': 'world'}, shell='tcsh')
        assert os.environ['TEST_ENV_VAR3'] == 'hello'
        assert os.environ['TEST_ENV_VAR4'] == 'world'

    def test_logfile(self, tmpdir):
        logfile = StringIO()
        tcsh('echo line1; echo line2', logfile=logfile)
        logfile.seek(0)
        outlines = logfile.read().splitlines()
        assert outlines[0].startswith('Tcsh-')
        assert outlines[1] == ''
        assert outlines[2] == 'line1'
        assert outlines[3] == 'line2'
        assert outlines[4].startswith('Tcsh')


if __name__ == "__main__":
    unittest.main()

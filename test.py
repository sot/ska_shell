import os
import unittest
from StringIO import StringIO
from Ska.Shell import Spawn, RunTimeoutError

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


if __name__ == "__main__":
    unittest.main()

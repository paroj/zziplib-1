import unittest
import subprocess
import logging
import inspect
import os
import collections
import urllib
import shutil
import random
import re
from fnmatch import fnmatchcase as matches
from cStringIO import StringIO

logg = logging.getLogger("test")

topsrcdir = "../.."
testdatadir = "testdata.d"
readme = "README"
mkzip = "zip"
unzip = "unzip"
exeext = ""

def shell_string(command):
   return " ".join(["'%s'" % arg.replace("'","\\'") for arg in command])

def shell(command, shell=True, calls=False, cwd=None, env=None, lang=None, returncodes=None):
    returncodes = returncodes or [ None, 0 ]
    Shell = collections.namedtuple("Shell",["returncode", "output", "errors", "shell"])
    if isinstance(command, basestring):
       sh_command = command
       command = [ command ]
    else:
       sh_command = shell_string(command)
    if not env: 
        env = os.environ.copy()
    if lang:
        for name, value in env.items():
            if name.startswith("LC_"):
                env[name] = lang
        env["LANG"] = lang # defines message format
        env["LC_ALL"] = lang # other locale formats
    build_libs = os.path.dirname(os.path.dirname(os.path.realpath(command[0])))+"/zzip/.libs"
    if os.path.isdir(build_libs):
        env["LD_LIBRARY_PATH"] = build_libs
    try:
        output, errors = "", ""
        if calls:
            logg.debug("result from %s: %s", cwd and cwd+"/" or "shell", sh_command)
            run = subprocess.Popen(command, shell=shell, cwd=cwd, env=env)
            if run.returncode:
                logg.warning("EXIT %s: %s", run.returncode, command)
            run.wait()
        else:
            logg.debug("output from %s: %s", cwd and cwd+"/" or "shell", sh_command)
            run = subprocess.Popen(command, shell=shell, cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=None, env=env)
            if run.returncode:
                logg.warning("EXIT %s: %s", run.returncode, command)
            output, errors = run.communicate() # run.wait()
    except:
        logg.error("*E*: %s", sh_command)
        for line in output.split("\n"):
            if line:
                logg.error("OUT: %s", line)
        for line in errors.split("\n"):
            if line:
                logg.error("ERR: %s", line)
        raise
    if run.returncode not in returncodes:
        logg.warning("*%02i: %s", run.returncode, sh_command)
        for line in output.split("\n"):
            if line:
                logg.warning("OUT: %s", line)
        for line in errors.split("\n"):
            if line:
                logg.warning("ERR: %s", line)
        raise subprocess.CalledProcessError(run.returncode, sh_command, output)
    else:
        for line in output.split("\n"):
            if line:
                logg.debug("OUT: %s", line)
        for line in errors.split("\n"):
            if line:
                logg.debug("ERR: %s", line)
    return Shell(run.returncode, output, errors, sh_command)

def get_caller_name():
    frame = inspect.currentframe().f_back.f_back
    return frame.f_code.co_name
def get_caller_caller_name():
    frame = inspect.currentframe().f_back.f_back.f_back
    return frame.f_code.co_name

def download(base_url, filename, into):
    data = "tmp.download"
    if not os.path.isdir(data):
        os.makedirs(data)
    subname = urllib.quote_plus(base_url)
    subdir = os.path.join(data, subname)
    if not os.path.isdir(subdir):
        os.makedirs(subdir)
    subfile = os.path.join(subdir, filename)
    if not os.path.exists(subfile):
       logg.info("need %s", subfile)
       d = urllib.urlopen(base_url + "/" + filename)
       f = open(subfile, "w")
       f.write(d.read())
       f.close()
    #
    if not os.path.isdir(into):
        os.makedirs(into)
    shutil.copy(subfile, into)
    return filename

def output(cmd, shell=True):
    run = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE)
    out, err = run.communicate()
    return out
def grep(pattern, lines):
    if isinstance(lines, basestring):
        lines = lines.split("\n")
    for line in lines:
       if re.search(pattern, line.rstrip()):
           yield line.rstrip()
def greps(lines, pattern):
    return list(grep(pattern, lines))
def all_errors(lines):
    if isinstance(lines, basestring):
        lines = lines.split("\n")
    for line in lines:
        if not line.strip():
            continue
        if "DEBUG:" in line:
            continue
        if "HINT:" in line:
            continue
        yield line.rstrip()
def errors(lines):
    return list(all_errors(lines))

class ZZipTest(unittest.TestCase):
  @property
  def t(self):
        if not os.path.isdir(testdatadir):
            os.makedirs(testdatadir)
        return testdatdir
  @property
  def s(self):
    return topsrcdir
  def src(self, name):
    return os.path.join(self.s, name)
  def readme(self):
    f = open(self.src(readme))
    text = f.read()
    f.close()
    return text
  def mkfile(self, name, content):
    b = os.path.dirname(name)
    if not os.path.isdir(b):
        os.makedirs(b)
    f = open(name, "w")
    f.write(content)
    f.close()
  def bins(self, name):
    if name == "unzip": return unzip
    if name == "mkzip": return mkzip
    exe = os.path.join("..", "bins", name)
    if exeext: exe += exeext
    return exe
  def gentext(self, size):
    random.seed(1234567891234567890)
    result = StringIO()
    old1 = ''
    old2 = ''
    for i in xrange(size):
        while True:
            x = random.choice("       abcdefghijklmnopqrstuvwxyz\n")
            if x == old1 or x == old2: continue
            old1 = old2
            old2 = x
            break
        result.write(x)
    return result.getvalue()
  def caller_testname(self):
    name = get_caller_caller_name()
    x1 = name.find("_")
    if x1 < 0: return name
    x2 = name.find("_", x1+1)
    if x2 < 0: return name
    return name[:x2]
  def testname(self, suffix = None):
    name = self.caller_testname()
    if suffix:
        return name + "_" + suffix
    return name
  def testzip(self, testname = None):
    testname = testname or self.caller_testname()
    zipname = testname + ".zip"
    return zipname
  def testdir(self, testname = None):
    testname = testname or self.caller_testname()
    newdir = "tmp."+testname
    if os.path.isdir(newdir):
        shutil.rmtree(newdir)
    os.makedirs(newdir)
    return newdir
  def rm_testdir(self, testname = None):
    testname = testname or self.caller_testname()
    newdir = "tmp."+testname
    if os.path.isdir(newdir):
        shutil.rmtree(newdir)
    return newdir
  def rm_testzip(self, testname = None):
    testname = testname or self.caller_testname()
    zipname = testname + ".zip"
    if os.path.exists(zipname):
        os.remove(zipname)
    return True
  ################################################################
  def test_1000_make_test0_zip(self):
    """ create a test.zip for later tests using standard 'zip'
    It will fall back to a variant in the source code if 'zip'
    is not installed on the build host. The content is just
    the README file that we can check for equality later on. """
    zipfile="test0.zip"
    tmpdir="test0.tmp"
    exe=self.bins("mkzip")
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} ../{zipfile} README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 10)
  def test_10001_make_test1_zip(self):
    """ create a test1.zip for later tests using standard 'zip'
    It will fall back to a variant in the source code if 'zip'
    is not installed on the build host. The archive has 10
    generic files that we can check for their content later. """
    zipfile="test1.zip"
    tmpdir="test1.tmp"
    exe=self.bins("mkzip")
    for i in [1,2,3,4,5,6,7,8,9]:
       filename = os.path.join(tmpdir,"file.%i" % i)
       filetext = "file-%i\n" % i
       self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} ../{zipfile} ??*.* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 10)
  def test_10002_make_test2_zip(self):
    """ create a test2.zip for later tests using standard 'zip'
    It will NOT fall back to a variant in the source code.
    The archive has 100 generic files with known content. """
    zipfile="test2.zip"
    tmpdir="test2.tmp"
    exe=self.bins("mkzip")
    for i in xrange(100):
       filename = os.path.join(tmpdir,"file.%02i" % i)
       filetext = "file-%02i\n" % i
       self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} ../{zipfile} ??*.* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 10)
  def test_10003_make_test3_zip(self):
    """ create a test3.zip for later tests using standard 'zip'
    It will NOT fall back to a variant in the source code.
    The archive has 1000 generic files with known content. """
    zipfile="test3.zip"
    tmpdir="test3.tmp"
    exe=self.bins("mkzip")
    for i in xrange(1000):
       filename = os.path.join(tmpdir,"file.%03i" % i)
       filetext = "file-%03i\n" % i
       self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} ../{zipfile} ??*.* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 10)
  def test_10004_make_test4_zip(self):
    """ create a test4.zip for later tests using standard 'zip'
    It will NOT fall back to a variant in the source code.
    The archive has 10000 generic files with known content
    and they are stored (NOT compressed) in the archive. """
    zipfile="test4.zip"
    tmpdir="test4.tmp"
    exe=self.bins("mkzip")
    for i in xrange(10000):
       filename = os.path.join(tmpdir,"file%04i.txt" % i)
       filetext = "file-%04i\n" % i
       self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} -n README ../{zipfile} ??*.* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 1000000)
  def test_10005_make_test5_zip(self):
    """ create a test5.zip for later tests using standard 'zip'
    It will NOT fall back to a variant in the source code.
    The archive has files at multiple subdirectories depth
    and of varying sizes each. """
    zipfile="test5.zip"
    tmpdir="test5.tmp"
    exe=self.bins("mkzip")
    for depth in xrange(20):
      dirpath = ""
      for i in xrange(depth):
        if i:
          dirpath += "subdir%i/" % i
      for size in xrange(18):
        size = 2 ** size
        filetext = self.gentext(size)
        filepart = "file%i-%i.txt" % (depth, size)
        filename = os.path.join(tmpdir, dirpath + filepart )
        self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    shell("{exe} ../{zipfile} -r file* subdir* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 1000000)
  def test_10010_make_test0_dat(self):
    """ create test.dat from test.zip with xorcopy """
    zipfile = "test0.zip"
    datfile = "test0x.dat"
    exe = self.bins("zzxorcopy")
    shell("{exe} {zipfile} {datfile}".format(**locals()))
    self.assertGreater(os.path.getsize(datfile), 10)
    self.assertEqual(os.path.getsize(datfile), os.path.getsize(zipfile))
  def test_10011_make_test1_dat(self):
    """ create test.dat from test.zip with xorcopy """
    zipfile = "test1.zip"
    datfile = "test1x.dat"
    exe = self.bins("zzxorcopy")
    shell("{exe} {zipfile} {datfile}".format(**locals()))
    self.assertGreater(os.path.getsize(datfile), 10)
    self.assertEqual(os.path.getsize(datfile), os.path.getsize(zipfile))
  def test_10012_make_test2_dat(self):
    """ create test.dat from test.zip with xorcopy """
    zipfile = "test2.zip"
    datfile = "test2x.dat"
    exe = self.bins("zzxorcopy")
    shell("{exe} {zipfile} {datfile}".format(**locals()))
    self.assertGreater(os.path.getsize(datfile), 10)
    self.assertEqual(os.path.getsize(datfile), os.path.getsize(zipfile))
  def test_10013_make_test3_dat(self):
    """ create test.dat from test.zip with xorcopy """
    zipfile = "test3.zip"
    datfile = "test3x.dat"
    exe = self.bins("zzxorcopy")
    shell("{exe} {zipfile} {datfile}".format(**locals()))
    self.assertGreater(os.path.getsize(datfile), 10)
    self.assertEqual(os.path.getsize(datfile), os.path.getsize(zipfile))
  def test_10014_make_test4_dat(self):
    """ create test.dat from test.zip with xorcopy """
    zipfile = "test4.zip"
    datfile = "test4x.dat"
    exe = self.bins("zzxorcopy")
    shell("{exe} {zipfile} {datfile}".format(**locals()))
    self.assertGreater(os.path.getsize(datfile), 10)
    self.assertEqual(os.path.getsize(datfile), os.path.getsize(zipfile))
  def test_20000_zziptest_test0_zip(self):
    """ run zziptest on test.zip """
    zipfile = "test0.zip"
    logfile = "test0.log"
    exe = self.bins("zziptest")
    shell("{exe} --quick {zipfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
  def test_20001_zziptest_test1_zip(self):
    """ run zziptest on test.zip """
    zipfile = "test1.zip"
    logfile = "test1.log"
    exe = self.bins("zziptest")
    shell("{exe} --quick {zipfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
  def test_20002_zziptest_test2_zip(self):
    """ run zziptest on test.zip """
    zipfile = "test2.zip"
    logfile = "test2.log"
    exe = self.bins("zziptest")
    shell("{exe} --quick {zipfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
  def test_20003_zziptest_test3_zip(self):
    """ run zziptest on test.zip """
    zipfile = "test3.zip"
    logfile = "test3.log"
    exe = self.bins("zziptest")
    shell("{exe} --quick {zipfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
  def test_20004_zziptest_test4_zip(self):
    """ run zziptest on test.zip """
    zipfile = "test4.zip"
    logfile = "test4.log"
    exe = self.bins("zziptest")
    shell("{exe} --quick {zipfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
  def test_20010_zzcat_test0_zip(self):
    """ run zzcat on test.zip using just test/README """
    zipfile = "test0.zip"
    getfile = "test0/README"
    logfile = "test0.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20011_zzcat_test1_zip(self):
    """ run zzcat on test.zip using just test/README """
    zipfile = "test1.zip"
    getfile = "test1/README"
    logfile = "test1.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test1/file.1"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20012_zzcat_test2_zip(self):
    """ run zzcat on test.zip using just test/README """
    zipfile = "test2.zip"
    getfile = "test2/README"
    logfile = "test2.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test2/file.22"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20013_zzcat_test3_zip(self):
    """ run zzcat on test.zip using just test/README """
    zipfile = "test3.zip"
    getfile = "test3/README"
    logfile = "test3.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test3/file.999"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-999\n", run.output)
  def test_20014_zzcat_test4_zip(self):
    """ run zzcat on test.zip using just test/README """
    zipfile = "test4.zip"
    getfile = "test4/README"
    logfile = "test4.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test4/file9999.txt"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-9999\n", run.output)
  def test_20020_zzdir_test0_zip(self):
    """ run zzdir on test0.zip using just 'test0' """
    zipfile = "test0.zip"
    getfile = "test0"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertLess(len(run.output), 30)
  def test_20021_zzdir_test1_zip(self):
    """ run zzdir on test1.zip using just 'test1' """
    zipfile = "test1.zip"
    getfile = "test1"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20022_zzdir_test2_zip(self):
    """ run zzdir on test2.zip using just 'test2' """
    zipfile = "test2.zip"
    getfile = "test2"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20023_zzdir_test3_zip(self):
    """ run zzdir on test3.zip using just 'test3' """
    zipfile = "test3.zip"
    getfile = "test3"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20024_zzdir_test4_zip(self):
    """ run zzdir on test4.zip using just 'test4' """
    zipfile = "test4.zip"
    getfile = "test4"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
    self.assertNotIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20320_zzxordir_test0_dat(self):
    """ run zzxordir on test0x.dat """
    zipfile = "test0x.dat"
    getfile = "test0x.dat"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()), returncodes = [0,1])
    self.assertEqual(run.returncode, 1)
    self.assertEqual("", run.output)
    self.assertIn("did not open test", run.errors)
    exe = self.bins("zzxordir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertLess(len(run.output), 30)
  def test_20321_zzxordir_test1_dat(self):
    """ run zzxordir on test1x.dat using just 'test1x' """
    zipfile = "test1x.dat"
    getfile = "test1x.dat"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()), returncodes = [0,1])
    self.assertEqual(run.returncode, 1)
    self.assertEqual("", run.output)
    self.assertIn("did not open test", run.errors)
    exe = self.bins("zzxordir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20322_zzxordir_test2_dat(self):
    """ run zzxordir on test2x.dat using just 'test2x' """
    zipfile = "test2x.dat"
    getfile = "test2x"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()), returncodes = [0,1])
    self.assertEqual(run.returncode, 1)
    self.assertEqual("", run.output)
    self.assertIn("did not open test", run.errors)
    exe = self.bins("zzxordir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20323_zzxordir_test3_dat(self):
    """ run zzxordir on test3x.dat using just 'test3x' """
    zipfile = "test3x.dat"
    getfile = "test3x"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()), returncodes = [0,1])
    self.assertEqual(run.returncode, 1)
    self.assertEqual("", run.output)
    self.assertIn("did not open test", run.errors)
    exe = self.bins("zzxordir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20324_zzxordir_test4_zip(self):
    """ run zzxordir on test4x.dat using just 'test4x' """
    zipfile = "test4x.dat"
    getfile = "test4x"
    exe = self.bins("zzdir")
    run = shell("{exe} {getfile} ".format(**locals()), returncodes = [0,1])
    self.assertEqual(run.returncode, 1)
    self.assertEqual("", run.output)
    self.assertIn("did not open test", run.errors)
    exe = self.bins("zzxordir")
    run = shell("{exe} {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
    self.assertNotIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20340_zzxorcat_test0_zip(self):
    """ run zzxorcat on testx.zip using just testx/README """
    getfile = "test0x/README"
    logfile = "test0x.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} ".format(**locals()), lang="C")
    self.assertEqual("", run.output)
    self.assertIn("No such file or directory", run.errors)
    exe = self.bins("zzxorcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20341_zzxorcat_test1_zip(self):
    """ run zzxorcat on testx.zip using just testx/README """
    getfile = "test1x/README"
    logfile = "test1x.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} ".format(**locals()), lang="C")
    self.assertEqual("", run.output)
    self.assertIn("No such file or directory", run.errors)
    exe = self.bins("zzxorcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test1x/file.1"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20342_zzxorcat_test2_zip(self):
    """ run zzxorcat on testx.zip using just testx/README """
    getfile = "test2x/README"
    logfile = "test2x.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} ".format(**locals()), lang="C")
    self.assertEqual("", run.output)
    self.assertIn("No such file or directory", run.errors)
    exe = self.bins("zzxorcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test2x/file.22"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20343_zzxorcat_test3_zip(self):
    """ run zzxorcat on testx.zip using just testx/README """
    getfile = "test3x/README"
    logfile = "test3x.readme.txt"
    exe = self.bins("zzcat")
    run = shell("{exe} {getfile} ".format(**locals()), lang="C")
    self.assertEqual("", run.output)
    self.assertIn("No such file or directory", run.errors)
    exe = self.bins("zzxorcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test3x/file.999"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-999\n", run.output)
  def test_20344_zzxorcat_test4_zip(self):
    """ run zzxorcat on testx.zip using just testx/README """
    getfile = "test4x/README"
    logfile = "test4x.readme.txt"
    exe = self.bins("zzxorcat")
    run = shell("{exe} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "test4x/file9999.txt"
    run = shell("{exe} {getfile}".format(**locals()))
    self.assertEqual("file-9999\n", run.output)
  #####################################################################
  # check unzzip
  #####################################################################
  def test_20400_infozip_cat_test0_zip(self):
    """ run inzo-zip cat test.zip using just archive README """
    zipfile = "test0.zip"
    getfile = "README"
    logfile = "test0.readme.pk.txt"
    exe = self.bins("unzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20401_infozip_cat_test1_zip(self):
    """ run info-zip cat test.zip using just archive README """
    zipfile = "test1.zip"
    getfile = "README"
    logfile = "test1.readme.pk.txt"
    exe = self.bins("unzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.1"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20402_infozip_cat_test2_zip(self):
    """ run info-zip cat test.zip using just archive README """
    zipfile = "test2.zip"
    getfile = "README"
    logfile = "test2.readme.pk.txt"
    exe = self.bins("unzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.22"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20405_zzcat_big_test5_zip(self):
    """ run info-zip cat test.zip using archive README """
    zipfile = "test5.zip"
    getfile = "README"
    logfile = "test5.readme.pk.txt"
    exe = self.bins("unzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "subdir1/subdir2/subdir3/subdir4/subdir5/subdir6/file7-1024.txt"
    compare = self.gentext(1024)
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual(compare, run.output)
  def test_20410_zzcat_big_test0_zip(self):
    """ run zzcat-big on test.zip using just archive README """
    zipfile = "test0.zip"
    getfile = "README"
    logfile = "test0.readme.big.txt"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20411_zzcat_big_test1_zip(self):
    """ run zzcat-big on test.zip using just archive README """
    zipfile = "test1.zip"
    getfile = "README"
    logfile = "test1.readme.big.txt"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.1"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20412_zzcat_big_test2_zip(self):
    """ run zzcat-seeke on test.zip using just archive README """
    zipfile = "test2.zip"
    getfile = "README"
    logfile = "test2.readme.big.txt"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.22"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20415_zzcat_big_test5_zip(self):
    """ run zzcat-big on test.zip using archive README """
    zipfile = "test5.zip"
    getfile = "README"
    logfile = "test5.readme.zap.txt"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "subdir1/subdir2/subdir3/subdir4/subdir5/subdir6/file7-1024.txt"
    compare = self.gentext(1024)
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual(compare, run.output)
  def test_20420_zzcat_mem_test0_zip(self):
    """ run zzcat-mem on test.zip using just archive README """
    zipfile = "test0.zip"
    getfile = "README"
    logfile = "test0.readme.mem.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20421_zzcat_mem_test1_zip(self):
    """ run zzcat-mem on test.zip using archive README """
    zipfile = "test1.zip"
    getfile = "README"
    logfile = "test1.readme.mem.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile}  {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.1"
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20422_zzcat_mem_test2_zip(self):
    """ run zzcat-mem on test.zip using archive README """
    zipfile = "test2.zip"
    getfile = "README"
    logfile = "test2.readme.mem.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.22"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20423_zzcat_mem_test3_zip(self):
    """ run zzcat-mem on test.zip using archive README """
    zipfile = "test3.zip"
    getfile = "README"
    logfile = "test3.readme.mem.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.999"
    run = shell("{exe} -p {zipfile}  {getfile}".format(**locals()))
    self.assertEqual("file-999\n", run.output)
  def test_20424_zzcat_mem_test4_zip(self):
    """ run zzcat-mem on test.zip using archive README """
    zipfile = "test4.zip"
    getfile = "README"
    logfile = "test4.readme.mem.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file9999.txt"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-9999\n", run.output)
  def test_20425_zzcat_mem_test5_zip(self):
    """ run zzcat-mem on test.zip using archive README """
    zipfile = "test5.zip"
    getfile = "README"
    logfile = "test5.readme.zap.txt"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "subdir1/subdir2/subdir3/subdir4/subdir5/subdir6/file7-1024.txt"
    compare = self.gentext(1024)
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual(compare, run.output)
  def test_20430_zzcat_mix_test0_zip(self):
    """ run zzcat-mix on test.zip using just archive README """
    zipfile = "test0.zip"
    getfile = "README"
    logfile = "test0.readme.mix.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20431_zzcat_mix_test1_zip(self):
    """ run zzcat-mix on test.zip using archive README """
    zipfile = "test1.zip"
    getfile = "README"
    logfile = "test1.readme.mix.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile}  {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.1"
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20432_zzcat_mix_test2_zip(self):
    """ run zzcat-mix on test.zip using archive README """
    zipfile = "test2.zip"
    getfile = "README"
    logfile = "test2.readme.mix.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.22"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20433_zzcat_mix_test3_zip(self):
    """ run zzcat-mix on test.zip using archive README """
    zipfile = "test3.zip"
    getfile = "README"
    logfile = "test3.readme.mix.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.999"
    run = shell("{exe} -p {zipfile}  {getfile}".format(**locals()))
    self.assertEqual("file-999\n", run.output)
  def test_20434_zzcat_mix_test4_zip(self):
    """ run zzcat-mix on test.zip using archive README """
    zipfile = "test4.zip"
    getfile = "README"
    logfile = "test4.readme.mix.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file9999.txt"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-9999\n", run.output)
  def test_20435_zzcat_mix_test5_zip(self):
    """ run zzcat-mix on test.zip using archive README """
    zipfile = "test5.zip"
    getfile = "README"
    logfile = "test5.readme.zap.txt"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "subdir1/subdir2/subdir3/subdir4/subdir5/subdir6/file7-1024.txt"
    compare = self.gentext(1024)
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual(compare, run.output)
  def test_20440_zzcat_zap_test0_zip(self):
    """ run zzcat-zap on test.zip using just archive README """
    zipfile = "test0.zip"
    getfile = "README"
    logfile = "test0.readme.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
  def test_20441_zzcat_zap_test1_zip(self):
    """ run zzcat-zap on test.zip using archive README """
    zipfile = "test1.zip"
    getfile = "README"
    logfile = "test1.readme.zap.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile}  {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.1"
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertEqual("file-1\n", run.output)
  def test_20442_zzcat_zap_test2_zip(self):
    """ run zzcat-zap on test.zip using archive README """
    zipfile = "test2.zip"
    getfile = "README"
    logfile = "test2.readme.zap.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.22"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-22\n", run.output)
  def test_20443_zzcat_zap_test3_zip(self):
    """ run zzcat-zap on test.zip using archive README """
    zipfile = "test3.zip"
    getfile = "README"
    logfile = "test3.readme.zap.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file.999"
    run = shell("{exe} -p {zipfile}  {getfile}".format(**locals()))
    self.assertEqual("file-999\n", run.output)
  def test_20444_zzcat_zap_test4_zip(self):
    """ run zzcat-zap on test.zip using archive README """
    zipfile = "test4.zip"
    getfile = "README"
    logfile = "test4.readme.zap.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "file9999.txt"
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual("file-9999\n", run.output)
  def test_20445_zzcat_zap_test5_zip(self):
    """ run zzcat-zap on test.zip using archive README """
    zipfile = "test5.zip"
    getfile = "README"
    logfile = "test5.readme.zap.txt"
    exe = self.bins("unzzip")
    run = shell("{exe} -p {zipfile} {getfile} | tee {logfile}".format(**locals()))
    self.assertGreater(os.path.getsize(logfile), 10)
    self.assertEqual(run.output.split("\n"), self.readme().split("\n"))
    getfile = "subdir1/subdir2/subdir3/subdir4/subdir5/subdir6/file7-1024.txt"
    compare = self.gentext(1024)
    run = shell("{exe} -p {zipfile} {getfile}".format(**locals()))
    self.assertEqual(compare, run.output)

  def test_20500_infozipdir_test0_zip(self):
    """ run info-zip dir test0.zip  """
    zipfile = "test0.zip"
    getfile = "test0.zip"
    exe = self.bins("unzip")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertLess(len(run.output), 230)
  def test_20501_infozipdir_test1_zip(self):
    """ run info-zip dir test1.zip  """
    zipfile = "test1.zip"
    getfile = "test1.zip"
    exe = self.bins("unzip")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
  def test_20502_infozipdir_big_test2_zip(self):
    """ run info-zip dir test2.zip """
    zipfile = "test2.zip"
    getfile = "test2.zip"
    exe = self.bins("unzip")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
  def test_20503_infozipdir_big_test3_zip(self):
    """ run info-zip dir test3.zip  """
    zipfile = "test3.zip"
    getfile = "test3.zip"
    exe = self.bins("unzip")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
  def test_20504_infozipdir_big_test4_zip(self):
    """ run info-zip dir test4.zip """
    zipfile = "test4.zip"
    getfile = "test4.zip"
    exe = self.bins("unzip")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
  def test_20505_infozipdir_big_test5_zip(self):
    """ run info-zip dir on test5.zip """
    zipfile = "test5.zip"
    getfile = "test5.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn('/subdir14/file15-128.txt\n', run.output)
    self.assertIn('/subdir5/subdir6/', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20510_zzdir_big_test0_zip(self):
    """ run zzdir-big on test0.zip  """
    zipfile = "test0.zip"
    getfile = "test0.zip"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertLess(len(run.output), 30)
  def test_20511_zzdir_big_test1_zip(self):
    """ run zzdir-big on test1.zip  """
    zipfile = "test1.zip"
    getfile = "test1.zip"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
  def test_20512_zzdir_big_test2_zip(self):
    """ run zzdir-big on test2.zip """
    zipfile = "test2.zip"
    getfile = "test2.zip"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
  def test_20513_zzdir_big_test3_zip(self):
    """ run zzdir-big on test3.zip  """
    zipfile = "test3.zip"
    getfile = "test3.zip"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
  def test_20514_zzdir_big_test4_zip(self):
    """ run zzdir-big on test4.zip """
    zipfile = "test4.zip"
    getfile = "test4.zip"
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
  def test_20515_zzdir_big_test5_zip(self):
    """ run zzdir-big on test5.zip """
    zipfile = "test5.zip"
    getfile = "test5.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn('/subdir14/file15-128.txt\n', run.output)
    self.assertIn('/subdir5/subdir6/', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20520_zzdir_mem_test0_zip(self):
    """ run zzdir-mem on test0.zip  """
    zipfile = "test0.zip"
    getfile = "test0.zip"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertLess(len(run.output), 30)
  def test_20521_zzdir_mem_test1_zip(self):
    """ run zzdir-mem on test1.zip  """
    zipfile = "test1.zip"
    getfile = "test1.zip"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20522_zzdir_mem_test2_zip(self):
    """ run zzdir-mem on test2.zip """
    zipfile = "test2.zip"
    getfile = "test2.zip"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20523_zzdir_mem_test3_zip(self):
    """ run zzdir-mem on test3.zip  """
    zipfile = "test3.zip"
    getfile = "test3.zip"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20524_zzdir_mem_test4_zip(self):
    """ run zzdir-mem on test4.zip """
    zipfile = "test4.zip"
    getfile = "test4.zip"
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
    self.assertNotIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20525_zzdir_mem_test5_zip(self):
    """ run zzdir-mem on test5.zip """
    zipfile = "test5.zip"
    getfile = "test5.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn('/subdir14/file15-128.txt\n', run.output)
    self.assertIn('/subdir5/subdir6/', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20530_zzdir_mix_test0_zip(self):
    """ run zzdir-mix on test0.zip  """
    # self.skipTest("todo")
    zipfile = "test0.zip"
    getfile = "test0.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertLess(len(run.output), 30)
  def test_20531_zzdir_mix_test1_zip(self):
    """ run zzdir-mix on test1.zip  """
    zipfile = "test1.zip"
    getfile = "test1.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20532_zzdir_mix_test2_zip(self):
    """ run zzdir-mix on test2.zip """
    zipfile = "test2.zip"
    getfile = "test2.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20533_zzdir_mix_test3_zip(self):
    """ run zzdir-mix on test3.zip  """
    zipfile = "test3.zip"
    getfile = "test3.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20534_zzdir_mix_test4_zip(self):
    """ run zzdir-mix on test4.zip """
    zipfile = "test4.zip"
    getfile = "test4.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
    self.assertNotIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20535_zzdir_mix_test5_zip(self):
    """ run zzdir-mix on test5.zip """
    zipfile = "test5.zip"
    getfile = "test5.zip"
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn('/subdir14/file15-128.txt\n', run.output)
    self.assertIn('/subdir5/subdir6/', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20540_zzdir_zap_test0_zip(self):
    """ run zzdir-zap on test0.zip  """
    zipfile = "test0.zip"
    getfile = "test0.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertLess(len(run.output), 30)
  def test_20541_zzdir_zap_test1_zip(self):
    """ run zzdir-zap on test1.zip  """
    zipfile = "test1.zip"
    getfile = "test1.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.1\n', run.output)
    self.assertIn(' file.2\n', run.output)
    self.assertIn(' file.9\n', run.output)
    self.assertIn(' README\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20542_zzdir_zap_test2_zip(self):
    """ run zzdir-zap on test2.zip """
    zipfile = "test2.zip"
    getfile = "test2.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.01\n', run.output)
    self.assertIn(' file.22\n', run.output)
    self.assertIn(' file.99\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20543_zzdir_zap_test3_zip(self):
    """ run zzdir-zap on test3.zip  """
    zipfile = "test3.zip"
    getfile = "test3.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file.001\n', run.output)
    self.assertIn(' file.222\n', run.output)
    self.assertIn(' file.999\n', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20544_zzdir_zap_test4_zip(self):
    """ run zzdir-zap on test4.zip """
    zipfile = "test4.zip"
    getfile = "test4.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn(' file0001.txt\n', run.output)
    self.assertIn(' file2222.txt\n', run.output)
    self.assertIn(' file9999.txt\n', run.output)
    self.assertNotIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20545_zzdir_zap_test5_zip(self):
    """ run zzdir-zap on test5.zip """
    zipfile = "test5.zip"
    getfile = "test5.zip"
    exe = self.bins("unzzip")
    run = shell("{exe} -v {getfile} ".format(**locals()))
    self.assertIn('/subdir14/file15-128.txt\n', run.output)
    self.assertIn('/subdir5/subdir6/', run.output)
    self.assertIn(' defl:N ', run.output)
    self.assertIn(' stored ', run.output)
  def test_20595_zzextract_zap_test5_zip(self):
    """ run zzextract-zap on test5.zip 
        => coughs up a SEGFAULT in zzip_dir_close() ?!?"""
    zipfile = "test5.zip"
    getfile = "test5.zip"
    tmpdir = self.testdir()
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} ../{getfile} ".format(**locals()))
    self.assertTrue(tmpdir+'/subdir1/subdir2/file3-1024.txt')
    self.rm_testdir()

  url_CVE_2017_5977 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5977 = "00153-zziplib-invalidread-zzip_mem_entry_extra_block"
  def test_59770_infozipdir_CVE_2017_5977(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 2])
    self.assertIn(" didn't find end-of-central-dir signature at end of central dir", run.errors)
    self.assertIn(" 2 extra bytes at beginning or within zipfile", run.errors)
    self.assertLess(len(run.output), 280)
    self.rm_testdir()
  def test_59771_zzipdir_big_CVE_2017_5977(self):
    """ run info-zip -l $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored test", run.output)
    self.rm_testdir()
  def test_59772_zzipdir_mem_CVE_2017_5977(self):
    """ run unzzip-mem -l $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  def test_59773_zzipdir_mix_CVE_2017_5977(self):
    """ run unzzip-mix -l $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  def test_59774_zzipdir_zap_CVE_2017_5977(self):
    """ run unzzip -l $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  def test_59775_zipext_info_CVE_2017_5977(self):
    """ run info' unzip $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [2])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 900)
    self.assertIn('test:  mismatching "local" filename', run.errors)
    self.assertIn('test:  unknown compression method', run.errors)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  def test_59776_zzipext_big_CVE_2017_5977(self):
    """ run unzzip-big $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59777_zzipext_mem_CVE_2017_5977(self):
    """ run unzzip-mem $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  def test_59778_zzipext_mix_CVE_2017_5977(self):
    """ run unzzip-mix $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  def test_59779_zzipext_zap_CVE_2017_5977(self):
    """ run unzzip $(CVE_2017_5977).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5977
    file_url = self.url_CVE_2017_5977
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3) # TODO
    self.rm_testdir()


  url_CVE_2017_5978 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5978 = "00156-zziplib-oobread-zzip_mem_entry_new"
  def test_59780_infozipdir_CVE_2017_5978(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertIn(' missing 4608 bytes in zipfile', run.errors)
    self.assertIn(' attempt to seek before beginning of zipfile', run.errors)
    self.assertLess(len(run.output), 80)
    self.assertLess(len(errors(run.errors)), 430)
    self.rm_testdir()
  def test_59781_zzipdir_big_CVE_2017_5978(self):
    """ run info-zip -l $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored (null)", run.output)
    self.rm_testdir()
  def test_59782_zzipdir_mem_CVE_2017_5978(self):
    """ run unzzip-mem -l $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn("zzip_mem_disk_load : unable to load entry", run.errors)
    self.assertIn("zzip_mem_disk_open : unable to load disk", run.errors)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59783_zzipdir_mix_CVE_2017_5978(self):
    """ run unzzip-mix -l $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn("zzip_mem_disk_load : unable to load entry", run.errors)
    self.assertIn("zzip_mem_disk_open : unable to load disk", run.errors)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59784_zzipdir_zap_CVE_2017_5978(self):
    """ run unzzip -l $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn("zzip_mem_disk_load : unable to load entry", run.errors)
    self.assertIn("zzip_mem_disk_open : unable to load disk", run.errors)
    self.rm_testdir()
  def test_59785_zipext_info_CVE_2017_5978(self):
    """ run info' unzip $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [3])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 900)
    self.assertIn('attempt to seek before beginning of zipfile', run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59786_zzipext_big_CVE_2017_5978(self):
    """ run unzzip-big $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  def test_59787_zzipext_mem_CVE_2017_5978(self):
    """ run unzzip-mem $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 300)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  def test_59788_zzipext_mix_CVE_2017_5978(self):
    """ run unzzip-mix $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 300)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59789_zzipext_zap_CVE_2017_5978(self):
    """ run unzzip $(CVE_2017_5978).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5978
    file_url = self.url_CVE_2017_5978
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 300)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 0)
    self.rm_testdir()

  url_CVE_2017_5979 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5979 = "00157-zziplib-nullptr-prescan_entry"
  def test_59790_infozipdir_CVE_2017_5979(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertIn(' 1 file', run.output)
    self.assertLess(len(run.output), 330)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_59791_zzipdir_big_CVE_2017_5979(self):
    """ run info-zip -l $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored a", run.output)
    self.rm_testdir()
  def test_59792_zzipdir_mem_CVE_2017_5979(self):
    """ run unzzip-mem -l $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 a", run.output)
    self.rm_testdir()
  def test_59793_zzipdir_mix_CVE_2017_5979(self):
    """ run unzzip-mix -l $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 a", run.output)
    self.rm_testdir()
  def test_59794_zzipdir_zap_CVE_2017_5979(self):
    """ run unzzip -l $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 a", run.output)
    self.rm_testdir()
  def test_59795_zipext_info_CVE_2017_5979(self):
    """ run info' unzip $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn('extracting: a', run.output)
    self.assertEqual(os.path.getsize(tmpdir+"/a"), 3)
    self.rm_testdir()
  def test_59796_zzipext_big_CVE_2017_5979(self):
    """ run unzzip-big $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/a"), 3)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59797_zzipext_mem_CVE_2017_5979(self):
    """ run unzzip-mem $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/a"), 3)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59798_zzipext_mix_CVE_2017_5979(self):
    """ run unzzip-mix $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 20)
    self.assertEqual(os.path.getsize(tmpdir+"/a"), 3)
    self.rm_testdir()
  # @unittest.expectedFailure
  def test_59799_zzipext_zap_CVE_2017_5979(self):
    """ run unzzip-mix $(CVE_2017_5979).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5979
    file_url = self.url_CVE_2017_5979
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 20)
    self.assertEqual(os.path.getsize(tmpdir+"/a"), 3)
    self.rm_testdir()


  url_CVE_2017_5974 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5974 = "00150-zziplib-heapoverflow-__zzip_get32"
  def test_59740_infozipdir_CVE_2017_5974(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn(' 1 file', run.output)
    self.assertLess(len(run.output), 330)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_59741_zzipdir_big_CVE_2017_5974(self):
    """ run unzzip-big -l $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored test", run.output)
    self.rm_testdir()
  def test_59742_zzipdir_mem_CVE_2017_5974(self):
    """ run unzzip-mem -l $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59743_zzipdir_mix_CVE_2017_5974(self):
    """ run unzzip-mix -l $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  def test_59744_zzipdir_zap_CVE_2017_5974(self):
    """ run unzzip -l $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" 3 test", run.output)
    self.rm_testdir()
  def test_59745_zzipext_zip_CVE_2017_5974(self):
    """ run info' unzip $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" extracting: test", run.output)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59746_zzipext_big_CVE_2017_5974(self):
    """ run unzzip-big $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59747_zzipext_mem_CVE_2017_5974(self):
    """ run unzzip-mem $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59748_zzipext_mix_CVE_2017_5974(self):
    """ run unzzip-mix $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59749_zzipext_zap_CVE_2017_5974(self):
    """ run unzzip $(CVE_2017_5974).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5974
    file_url = self.url_CVE_2017_5974
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()

  url_CVE_2017_5975 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5975 = "00151-zziplib-heapoverflow-__zzip_get64"
  def test_59750_infozipdir_CVE_2017_5975(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 2])
    self.assertIn(' missing 10 bytes in zipfile', run.errors)
    self.assertIn("didn't find end-of-central-dir signature at end of central dir", run.errors)
    self.assertIn(' 1 file', run.output)
    self.assertLess(len(run.output), 330)
    self.assertLess(len(errors(run.errors)), 430)
    self.rm_testdir()
  def test_59751_zzipdir_big_CVE_2017_5975(self):
    """ run info-zip -l $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored test", run.output)
    self.rm_testdir()
  def test_59752_zzipdir_mem_CVE_2017_5975(self):
    """ run unzzip-mem -l $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn("zzip_mem_disk_load : unable to load entry", run.errors)
    self.assertIn("zzip_mem_disk_open : unable to load disk", run.errors)
    self.rm_testdir()
  def test_59753_zzipdir_mix_CVE_2017_5975(self):
    """ run unzzip-mix -l $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn("zzip_mem_disk_load : unable to load entry", run.errors)
    self.assertIn("zzip_mem_disk_open : unable to load disk", run.errors)
    self.rm_testdir()
  def test_59754_zzipdir_zap_CVE_2017_5975(self):
    """ run unzzip -l $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_59755_zipext_info_CVE_2017_5975(self):
    """ run info' unzip $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [2])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 900)
    self.assertIn('file #1:  bad zipfile offset (local header sig):  127', run.errors)
    #self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59756_zzipext_big_CVE_2017_5975(self):
    """ run unzzip-big $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 0) # TODO
    self.rm_testdir()
  def test_59757_zzipext_mem_CVE_2017_5975(self):
    """ run unzzip-mem $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59758_zzipext_mix_CVE_2017_5975(self):
    """ run unzzip-mix $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59759_zzipext_zap_CVE_2017_5975(self):
    """ run unzzip $(CVE_2017_5975).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5975
    file_url = self.url_CVE_2017_5975
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn("..(nil)", run.errors)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()


  url_CVE_2017_5976 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5976 = "00152-zziplib-heapoverflow-zzip_mem_entry_extra_block"
  def test_59760_infozipdir_CVE_2017_5976(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 2])
    self.assertIn(' 27 extra bytes at beginning or within zipfile', run.errors)
    self.assertIn("didn't find end-of-central-dir signature at end of central dir", run.errors)
    self.assertIn(' 1 file', run.output)
    self.assertLess(len(run.output), 330)
    self.assertLess(len(errors(run.errors)), 500)
    self.rm_testdir()
  def test_59761_zzipdir_big_CVE_2017_5976(self):
    """ run info-zip -l $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored test", run.output)
    self.rm_testdir()
  def test_59762_zzipdir_mem_CVE_2017_5976(self):
    """ run unzzip-mem -l $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn("3 test", run.output)
    self.rm_testdir()
  def test_59763_zzipdir_mix_CVE_2017_5976(self):
    """ run unzzip-mix -l $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn("3 test", run.output)
    self.rm_testdir()
  def test_59764_zzipdir_zap_CVE_2017_5976(self):
    """ run unzzip -l $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 255])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn("3 test", run.output)
    self.rm_testdir()
  def test_59765_zipext_info_CVE_2017_5976(self):
    """ run info' unzip $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [2])
    self.assertLess(len(run.output), 190)
    self.assertLess(len(errors(run.errors)), 900)
    self.assertIn("extracting: test", run.output)
    self.assertIn('-27 bytes too long', run.errors)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    # self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59766_zzipext_big_CVE_2017_5976(self):
    """ run unzzip-big $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59767_zzipext_mem_CVE_2017_5976(self):
    """ run unzzip-mem $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 30) # TODO
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  @unittest.expectedFailure
  def test_59768_zzipext_mix_CVE_2017_5976(self):
    """ run unzzip-mix $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 30) # TODO
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59769_zzipext_zap_CVE_2017_5976(self):
    """ run unzzip $(CVE_2017_5976).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5976
    file_url = self.url_CVE_2017_5976
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 30)
    self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()

  url_CVE_2017_5980 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5980 = "00154-zziplib-nullptr-zzip_mem_entry_new"
  def test_59800_infozipdir_CVE_2017_5980(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 2])
    self.assertIn(' missing 6 bytes in zipfile', run.errors)
    self.assertIn("didn't find end-of-central-dir signature at end of central dir", run.errors)
    self.assertIn(' 1 file', run.output)
    self.assertLess(len(run.output), 330)
    self.assertLess(len(errors(run.errors)), 500)
    self.rm_testdir()
  def test_59801_zzipdir_big_CVE_2017_5980(self):
    """ run info-zip -l $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    self.assertIn(" stored (null)", run.output)
    self.rm_testdir()
  def test_59802_zzipdir_mem_CVE_2017_5980(self):
    """ run unzzip-mem -l $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertTrue(greps(run.errors, "unable to load disk"))
    self.rm_testdir()
  def test_59803_zzipdir_mix_CVE_2017_5980(self):
    """ run unzzip-mix -l $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [2])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertTrue(greps(run.errors, "Invalid or"))
    self.rm_testdir()
  def test_59804_zzipdir_zap_CVE_2017_5980(self):
    """ run unzzip -l $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 180)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_59805_zipext_info_CVE_2017_5980(self):
    """ run info' unzip $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [3])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 900)
    self.assertIn('file #1:  bad zipfile offset (lseek)', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59806_zzipext_big_CVE_2017_5980(self):
    """ run unzzip-big $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59807_zzipext_mem_CVE_2017_5980(self):
    """ run unzzip-mem $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59808_zzipext_mix_CVE_2017_5980(self):
    """ run unzzip-mix $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()
  def test_59809_zzipext_zap_CVE_2017_5980(self):
    """ run unzzip $(CVE_2017_5980).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5980
    file_url = self.url_CVE_2017_5980
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [3]) # TODO
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.rm_testdir()

  url_CVE_2017_5981 = "https://raw.githubusercontent.com/asarubbo/poc/master/"
  zip_CVE_2017_5981 = "00161-zziplib-assertionfailure-seeko_C"
  def test_59810_infozipdir_CVE_2017_5981(self):
    """ run info-zip dir test0.zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertIn(' missing 4 bytes in zipfile', run.errors)
    self.assertIn("zipfile corrupt", run.errors)
    self.assertLess(len(run.output), 80)
    self.assertLess(len(errors(run.errors)), 500)
    self.rm_testdir()
  def test_59811_zzipdir_big_CVE_2017_5981(self):
    """ run info-zip -l $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_59812_zzipdir_mem_CVE_2017_5981(self):
    """ run unzzip-mem -l $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_59813_zzipdir_mix_CVE_2017_5981(self):
    """ run unzzip-mix -l $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, "Invalid or"))
    self.rm_testdir()
  def test_59814_zzipdir_zap_CVE_2017_5981(self):
    """ run unzzip-zap -l $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 80)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_59815_zipext_info_CVE_2017_5981(self):
    """ run info' unzip $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [3])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 500)
    self.assertIn('zipfile corrupt.', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59816_zzipext_big_CVE_2017_5981(self):
    """ run unzzip-big $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59817_zzipext_mem_CVE_2017_5981(self):
    """ run unzzip-mem $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59818_zzipext_mix_CVE_2017_5981(self):
    """ run unzzip-mix $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_59819_zzipext_zap_CVE_2017_5981(self):
    """ run unzzip $(CVE_2017_5981).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2017_5981
    file_url = self.url_CVE_2017_5981
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()


  url_CVE_2018_10 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_10 = "zziplib_0-13-67_zzdir_invalid-memory-access_main.zip"
  def test_63010(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 80)
    self.assertLess(len(errors(run.errors)), 600)
    self.rm_testdir()
  def test_63011(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63012(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63013(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, "central directory not found"))
    self.rm_testdir()
  def test_63014(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 80)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_63015(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 600)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63016(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63017(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63018(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63019(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_10
    file_url = self.url_CVE_2018_10
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_11 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_11 = "zziplib_0-13-67_unzzip_infinite-loop_unzzip_cat_file.zip"
  def test_63110(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 600)
    self.rm_testdir()
  def test_63111(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63112(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63113(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, "central directory not found"))
    self.rm_testdir()
  def test_63114(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 90)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_63115(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 90)
    self.assertLess(len(errors(run.errors)), 600)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63116(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63117(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63118(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63119(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_11
    file_url = self.url_CVE_2018_11
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_12 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_12 = "zziplib_0-13-67_unzip-mem_buffer-access-with-incorrect-length-value_zzip_disk_fread.zip"
  def test_63810(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.rm_testdir()
  def test_63811(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63812(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_63813(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(grep(run.errors, "central directory not found"))
    self.rm_testdir()
  def test_63814(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_63815(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63816(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63817(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63818(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_63819(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_12
    file_url = self.url_CVE_2018_12
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_14 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_14 = "zziplib_0-13-67_zzdir_memory-alignment-errors___zzip_fetch_disk_trailer.zip"
  def test_64840(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.rm_testdir()
  def test_64841(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_64842(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.rm_testdir()
  def test_64843(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, "central directory not found"))
    self.rm_testdir()
  def test_64844(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_64845(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_64846(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_64847(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_64848(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_64849(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_14
    file_url = self.url_CVE_2018_14
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_15 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_15 = "zziplib_0-13-67_unzip-mem_memory-alignment-errors_zzip_disk_findfirst.zip"
  def test_65400(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.rm_testdir()
  def test_65401(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_65402(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_65403(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, ".zip: No medium found"))
    self.rm_testdir()
  def test_65404(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_65405(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65406(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65407(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65408(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65409(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_15
    file_url = self.url_CVE_2018_15
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_16 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_16 = "zziplib_0-13-67_unzzip_memory-aligment-errors___zzip_fetch_disk_trailer.zip"
  def test_65410(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.rm_testdir()
  def test_65411(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_65412(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_65413(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, ".zip: No medium found"))
    self.rm_testdir()
  def test_65414(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_65415(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65416(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65417(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65418(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65419(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_16
    file_url = self.url_CVE_2018_16
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()

  url_CVE_2018_17 = "https://github.com/ProbeFuzzer/poc/blob/master/zziplib"
  zip_CVE_2018_17 = "zziplib_0-13-67_unzip-mem_memory-alignment-errors_zzip_disk_findfirst_64.zip"
  def test_65420(self):
    """ info unzip -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 9])
    self.assertIn("End-of-central-directory signature not found", run.errors)
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.rm_testdir()
  def test_65421(self):
    """ unzzip-big -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.rm_testdir()
  def test_65422(self):
    """ unzzip-mem -l $(CVE).zip """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 1)
    self.rm_testdir()
  def test_65423(self):
    """ unzzip-mix -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 1)
    self.assertTrue(greps(run.errors, ".zip: No medium found"))
    self.rm_testdir()
  def test_65424(self):
    """ unzzip-zap -l $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("{exe} -l {tmpdir}/{filename} ".format(**locals()),
        returncodes = [0, 3])
    self.assertLess(len(run.output), 1)
    self.assertLess(len(errors(run.errors)), 200)
    self.assertIn(": Success", run.errors)
    self.rm_testdir()
  def test_65425(self):
    """ info unzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzip")
    run = shell("cd {tmpdir} && {exe} -o {filename}".format(**locals()),
        returncodes = [9])
    self.assertLess(len(run.output), 200)
    self.assertLess(len(errors(run.errors)), 800)
    self.assertIn('End-of-central-directory signature not found', run.errors)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65426(self):
    """ unzzip-big $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-big")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 1)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65427(self):
    """ unzzip-mem $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mem")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0])
    self.assertLess(len(run.output), 30)
    self.assertLess(len(errors(run.errors)), 10)
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65428(self):
    """ unzzip-mix $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip-mix")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,2])
    self.assertLess(len(run.output), 30)
    self.assertTrue(greps(run.errors, "No medium found"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()
  def test_65429(self):
    """ unzzip $(CVE).zip  """
    tmpdir = self.testdir()
    filename = self.zip_CVE_2018_17
    file_url = self.url_CVE_2018_17
    download(file_url, filename, tmpdir)
    exe = self.bins("unzzip")
    run = shell("cd {tmpdir} && ../{exe} {filename} ".format(**locals()),
        returncodes = [0,3])
    self.assertLess(len(run.output), 30)
    self.assertTrue(greps(run.errors, "central directory not found"))
    # self.assertEqual(os.path.getsize(tmpdir+"/test"), 3)
    self.assertFalse(os.path.exists(tmpdir+"/test"))
    self.rm_testdir()


  def test_91000_zzshowme_check_sfx(self):
    """ create an *.exe that can extract its own zip content """
    exe=self.bins("mkzip")
    exefile = "tmp.zzshowme" + exeext
    libstub = ".libs/zzipself" + exeext
    txtfile_name = readme
    txtfile = self.src(readme)
    # add the extract-stub so we have reserved the size
    run = shell("{exe} -0 -j {exefile}.zip {libstub}".format(**locals()))
    self.assertFalse(run.returncode)
    # add the actual content which may now be compressed
    run = shell("{exe} -9 -j {exefile}.zip {txtfile}".format(**locals()))
    self.assertFalse(run.returncode)
    # rename .zip to .exe and put the extract-stub at the start
    shutil.copy(exefile+".zip", exefile)
    setstub="./zzipsetstub" + exeext
    run = shell("{setstub} {exefile} {libstub}".format(**locals()))
    self.assertFalse(run.returncode)
    os.chmod(exefile, 0755)
    # now ask the new .exe to show some of its own content
    run = shell("./{exefile} {txtfile_name}".format(**locals()))
    self.assertFalse(run.returncode)
    txt = open(txtfile).read()
    self.assertEqual(txt.split("\n"), run.output.split("\n"))
    
  def test_99000_make_test1w_zip(self):
    """ create a test1w.zip using zzip/write functions. """
    exe=self.bins("zzip")
    run = shell("{exe} --version".format(**locals()))
    if "- NO -" in run.output:
        self.skipTest("- NO -D_ZZIP_ENABLE_WRITE")
        return
    zipfile=self.testzip()
    tmpdir=self.testdir()
    exe=self.bins("zzip")
    for i in [1,2,3,4,5,6,7,8,9]:
       filename = os.path.join(tmpdir,"file.%i" % i)
       filetext = "file-%i\n" % i
       self.mkfile(filename, filetext)
    filename = os.path.join(tmpdir,"README")
    filetext = self.readme()
    self.mkfile(filename, filetext)
    self.rm_zipfile()
    shell("../{exe} ../{zipfile} ??*.* README".format(**locals()), cwd=tmpdir)
    self.assertGreater(os.path.getsize(zipfile), 10)




if __name__ == "__main__":
  import optparse
  _o = optparse.OptionParser("%prog [options] test_xxx")
  _o.add_option("-b", "--topsrcdir", metavar="DIR", default=topsrcdir,
    help="path to the top srcdir / unpack directory [%default]")
  _o.add_option("-t", "--testdatadir", metavar="DIR", default=testdatadir,
    help="path where temporary testdata is created [%default]")
  _o.add_option("-Z", "--mkzip", metavar="EXE", default=mkzip,
    help="name or path to zip.exe for *.zip creation [%default]")
  _o.add_option("-U", "--unzip", metavar="EXE", default=unzip,
    help="name or path to unzip.exe to unpack *.zip [%default]")
  _o.add_option("-E", "--exeext", metavar="EXT", default=exeext,
    help="the executable extension (automake $(EXEEXT)) [%default]")
  _o.add_option("--xmlresults", action="store_true", default=False,
    help="print output in junit xml testresult format [%default]")
  _o.add_option("-v", "--verbose", action="count", default=0,
    help="increase logging output [%default]")
  opt, args = _o.parse_args()
  logging.basicConfig(level = logging.WARNING - 10 * opt.verbose)
  topsrcdir = opt.topsrcdir
  testdatdir = opt.testdatadir
  mkzip = opt.mkzip
  unzip = opt.unzip
  exeext = opt.exeext
  if not args: args += [ "test_" ]
  suite = unittest.TestSuite()
  for arg in args:
    for classname in sorted(list(globals())):
      if not classname.endswith("Test"):
        continue
      testclass = globals()[classname]
      for method in sorted(dir(testclass)):
        if "*" not in arg: arg += "*"
        if arg.startswith("_"): arg = arg[1:]
        if matches(method, arg):
          suite.addTest(testclass(method))
  # TextTestRunner(verbosity=opt.verbose).run(suite)
  if opt.xmlresults:
    import xmlrunner
    Runner = xmlrunner.XMLTestRunner
    Runner(xmlresults).run(suite)
  else:
    Runner = unittest.TextTestRunner
    Runner(verbosity=opt.verbose).run(suite)
 

# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

from Ska.Shell import __version__
try:
    from testr.setup_helper import cmdclass
except ImportError:
    cmdclass = {}

setup(name='Ska.Shell',
      author='Tom Aldcroft',
      description='Various shell utilities',
      author_email='taldcroft@cfa.harvard.edu',
      version=__version__,
      zip_safe=False,
      packages=['Ska', 'Ska.Shell', 'Ska.Shell.tests'],
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )

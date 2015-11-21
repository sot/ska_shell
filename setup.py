from setuptools import setup

from Ska.Shell import __version__

setup(name='Ska.Shell',
      author='Tom Aldcroft',
      description='Various shell utilities',
      author_email='taldcroft@cfa.harvard.edu',
      py_modules=['Ska.Shell'],
      test_suite='test',
      version=__version__,
      zip_safe=False,
      packages=['Ska'],
      package_dir={'Ska': 'Ska'},
      package_data={}
      )

from setuptools import setup

setup(name='Ska.Shell',
      author='Tom Aldcroft',
      description='Various shell utilities',
      author_email='taldcroft@cfa.harvard.edu',
      py_modules=['Ska.Shell'],
      test_suite='test',
      version='0.02',
      zip_safe=False,
      namespace_packages=['Ska'],
      packages=['Ska'],
      package_dir={'Ska': 'Ska'},
      package_data={}
      )

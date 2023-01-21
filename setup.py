# Licensed under a 3-clause BSD style license - see LICENSE.rst
from setuptools import setup

from ska_helpers.setup_helper import duplicate_package_info
from testr.setup_helper import cmdclass

name = "ska_shell"
namespace = "Ska.Shell"

packages = ["ska_shell", "ska_shell.tests"]
package_dir = {name: name}

duplicate_package_info(packages, name, namespace)
duplicate_package_info(package_dir, name, namespace)

setup(name=name,
      author='Tom Aldcroft',
      description='Various shell utilities',
      author_email='taldcroft@cfa.harvard.edu',
      use_scm_version=True,
      setup_requires=['setuptools_scm', 'setuptools_scm_git_archive'],
      zip_safe=False,
      packages=packages,
      package_dir=package_dir,
      tests_require=['pytest'],
      cmdclass=cmdclass,
      )

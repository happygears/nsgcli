import os
import setuptools
from nsgcli.version import __version__

readme_file = 'README_PYPI.md' if os.path.exists('README_PYPI.md') else 'README.md'
with open(readme_file, 'r', encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(name='nsgcli',
                 version=__version__,
                 description='NetSpyGlass CLI',
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 classifiers=[
                     'Development Status :: 4 - Beta',
                     'License :: OSI Approved :: Apache Software License',
                     'Programming Language :: Python :: 3.6',
                     'Programming Language :: Python :: 3.7',
                     'Programming Language :: Python :: 3.8',
                     'Programming Language :: Python :: 3.9',
                     'Topic :: System :: Networking :: Monitoring',
                 ],
                 keywords='network monitoring NMS netspyglass',
                 url='https://github.com/happygears/nsgcli',
                 author='Happy Gears, Inc',
                 author_email='vadim@happygears.net',
                 license='Apache',
                 packages=setuptools.find_packages(),
                 python_requires='>=3.6',
                 install_requires=[
                     'requests[socks]', 'requests-unixsocket', 'pyhocon', 'typing', 'python-dateutil', 'pytz', 'tabulate',
                     'gnmi-proto', 'pandas', 'jsonpath-ng'
                 ],
                 scripts=['bin/nsgcli', 'bin/nsgql', 'bin/silence', 'bin/nsggrok', 'bin/nsggnmi'],
                 include_package_data=True,
                 zip_safe=False)

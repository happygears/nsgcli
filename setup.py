import setuptools
from nsgcli.version import __version__

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(name='nsgcli',
                 version=__version__,
                 description='NetSpyGlass CLI',
                 long_description=long_description,
                 long_description_content_type="text/markdown",
                 classifiers=[
                     'Development Status :: 4 - Beta',
                     'License :: OSI Approved :: Apache Software License',
                     'Programming Language :: Python :: 2.7',
                     'Topic :: System :: Networking :: Monitoring',
                 ],
                 keywords='network monitoring NMS netspyglass',
                 url='https://github.com/happygears/nsgcli',
                 author='Happy Gears, Inc',
                 author_email='vadim@happygears.net',
                 license='Apache',
                 packages=setuptools.find_packages(),
                 include_package_data=True,
                 install_requires=[
                     'Click'
                 ],
                 entry_points='''
                    [console_scripts]
                    nsgcli=nsgcli.nsgcli_main:cli
                 ''',
                 )

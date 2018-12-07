import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(name='nsgcli',
                 version='1.0.21',
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
                 install_requires=[
                     'requests', 'requests-unixsocket', 'pyhocon', 'typing'
                 ],
                 scripts=['bin/nsgcli', 'bin/nsgql'],
                 include_package_data=True,
                 zip_safe=False)

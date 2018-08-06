from setuptools import setup

setup(name='nsgcli',
      version='1.0',
      description='NetSpyGlass CLI',
      long_description='NetSpyGlass Command Line Tools nsgcli and nsgql',
      classifiers=[
          'Development Status :: 4 - Beta',
          'License :: OSI Approved :: Apache Software License',
          'Programming Language :: Python :: 2.7',
          'Topic :: System :: Networking :: Monitoring',
      ],
      keywords='network monitoring NMS netspyglass',
      url='https://github.com/happygears/nw2',
      author='Happy Gears, Inc',
      author_email='vadim@happygears.net',
      license='Apache',
      packages=['nsgcli'],
      install_requires=[
          'requests', 'requests-unixsocket'
      ],
      scripts=['bin/nsgcli', 'bin/nsgql'],
      include_package_data=True,
      zip_safe=False)

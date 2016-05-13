#!/usr/bin/env python

from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
]

# http://stackoverflow.com/questions/2058802/how-can-i-get-the-version-defined-in-setup-py-setuptools-in-my-package
with open('m2mclient/_version.py') as f:
    exec(f.read())

long_desc = "Official Dataplicity M2M Client"
setup(
    name='m2mclient',
    version=VERSION,
    description="A client for the Dataplicity M2M server",
    long_description=long_desc,
    author='WildFoundry',
    author_email='support@dataplicity.com',
    url='https://www.dataplicity.com',
    platforms=['any'],
    packages=find_packages(),
    include_package_data=True,
    exclude_package_data={'': ['_*', 'docs/*']},
    classifiers=classifiers,

    install_requires=[
        'websocket-client',
        'enum34',
        'six'
    ]
)

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

with open('README.md') as f:
    long_desc = f.read()

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
    classifiers=classifiers,

    install_requires=[
        'websocket-client',
        'enum34',
        'six'
    ]
)

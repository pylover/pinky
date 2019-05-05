import os
import sys
import re

from setuptools import setup, find_packages


with open(
    os.path.join(os.path.dirname(__file__), 'pinkyserver.py')
) as v_file:
    package_version = \
        re.compile(r'.*__version__ = \'(.*?)\'', re.S) \
        .match(v_file.read()) \
        .group(1)


dependencies = [
    'nanohttp >= 1.11.1, < 2',
    'gunicorn',
    'RPi.GPIO',
]


setup(
    name='pinkyserver',
    version=package_version,
    author='Vahid Mardani',
    author_email='vahid.mardani@gmail.com',
    url='http://github.com/pylover/pinky',
    description= \
        'An opensource 3d-printed 3d printer with remote ' \
        'observation using json API and raspberrypi camera.',
    py_modules=['pinkyserver'],
    long_description=open('README.md').read(),
    install_requires=dependencies,
)



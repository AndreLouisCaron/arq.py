# -*- coding: utf-8 -*-


from setuptools import (
    find_packages,
    setup,
)


def readfile(path):
    with open(path, 'rb') as stream:
        return stream.read().decode('utf-8')


readme = readfile('README.rst')


setup(
    name='arq',
    url='https://github.com/AndreLouisCaron/arq.py',
    license='MIT',
    author='Andre Caron',
    author_email='andre.l.caron@gmail.com',
    description='ARQ implementations in Python, using Gevent',
    long_description=readme,
    keywords='arq udp gevent',
    version='0.0.0',
    packages=find_packages(where='src'),
    package_dir={
        '': 'src',
    },
)

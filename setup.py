#!/usr/bin/env python

from setuptools import setup

setup(name='youtube-sync',
        version='1.0',
        description='Maintains active repository of music in YouTube playlist',
        url='https://github.com/SajeOne/Youtube-Music-Sync',
        author='Shane "SajeOne" Brown',
        author_email='contact@shane-brown.ca',
        license='GPL3',
        zip_safe=False,
        package_dir={'youtube-sync': './'},
        packages=['youtube-sync'],
        scripts=['youtube-sync', 'mp3tags'])

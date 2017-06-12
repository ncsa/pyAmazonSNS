#!/usr/bin/env python

from setuptools import setup

setup(
    name="send_sns",
    version="1.0",
    author="sricola@github",
    description="Send notifications via AWS",
    install_requires=['boto3', 'tornado'],
    include_package_data=True,
    py_modules = ['send_sns'],
    entry_points = {
        'console_scripts': [
            'send_sns = send_sns:main',
        ]
    }
)

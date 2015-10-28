# -*- coding: utf-8 -*-
from setuptools import setup


setup(
    name='linaro-art',
    author='Miłosz Wasiewski',
    author_email='milosz.wasilewski@linaro.org',
    version="0.1",
    py_modules=['art'],
    description="It's all about the Art",

    install_requires=[
        'click==5.1',
        'requests==2.8.1',
        'tabulate==0.7.5'
    ],
    entry_points={
        'console_scripts': ['linaro-art = art:main']
    },
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    zip_safe=False,
)

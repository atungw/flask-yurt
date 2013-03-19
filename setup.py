"""
Flask-Yurt
-------------

Adds server-side session support using MongoDB to Flask
"""
from setuptools import setup


setup(
    name='Flask-Yurt',
    version='1.0',
    url='https://github.com/atungw/flask-yurt',
    license='MIT',
    author='Andrew Tung',
    author_email='atungw@gmail.com',
    description='Adds server-side session support using MongoDB to Flask',
    long_description=__doc__,
    py_modules=['flask_yurt'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'Flask'
        'PyMongo'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
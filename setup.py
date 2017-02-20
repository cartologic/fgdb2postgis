
from pip.req import parse_requirements
from setuptools import setup

requirements = parse_requirements('./requirements.txt', session=False)

setup(
    name='fgdb2postgis',
    version='0.1.4',
    description="""File geodatabase to postgis convertor""",
    long_description=open('README.rst').read(),
    author='George Ioannou',
    author_email='gmioannou@cartologic.com',
    url='https://github.com/cartologic/fgdb2postgis',
    packages=['fgdb2postgis'],
    package_data={'fgdb2postgis': ['sql_files/*.sql']},
    include_package_data=True,
    install_requires=[
        'numpy>=1.12.0',
        'psycopg2>=2.6.2',
        'pyyaml>=3.12',
        'archook==1.0.0',
    ],
    dependency_links=[
        'https://github.com/gmioannou/archook/tarball/master#egg=archook-1.0.0'
    ],
    license="MIT",
    keywords='fgdb2postgis',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering',
        'Operating System :: Microsoft :: Windows'
    ],
    entry_points={
        'console_scripts': ['fgdb2postgis = fgdb2postgis.__main__:main']
    },
)

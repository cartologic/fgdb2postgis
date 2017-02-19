
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
    packages=[
        'fgdb2postgis',
    ],
    package_data={'fgdb2postgis': ['sql_files/*.sql']},
    include_package_data=True,
    # install_requires=[],
    install_requires=[str(requirement.req) for requirement in requirements],
    license="MIT",
    zip_safe=False,
    keywords='fgdb2postgis',
    classifiers=[
        'Development Status :: 3 - Alpha',
    ],
    entry_points={
        'console_scripts': [
            'fgdb2postgis = fgdb2postgis.__main__:main',
        ],
    },
)

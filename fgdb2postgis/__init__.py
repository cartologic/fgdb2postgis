__author__ = 'George Ioannou'
__version__ = (0, 2, 8, 'rc', 0)


def get_current_version():
    from .version import get_version
    return get_version(__version__)

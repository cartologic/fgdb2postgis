__author__ = 'George Ioannou'
__version__ = (0, 3, 5, 'final', 0)

def get_current_version():
    from .version import get_version
    return get_version(__version__)

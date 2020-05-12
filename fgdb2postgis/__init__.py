__author__ = 'George Ioannou'
__version__ = (0, 3, 3, 'final', 0)

from fgdb2postgis.filegdb import FileGDB
from fgdb2postgis.postgis import PostGIS

def get_current_version():
    from .version import get_version
    return get_version(__version__)

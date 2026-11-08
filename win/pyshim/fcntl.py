# fcntl on Windows: the module is Unix-only, and upstream's dm/tools/tree_tar.py imports it at the top to flock the compile cache's parent folder.
# tree_tar takes an OSError from flock as "a drive without flock" and goes on without the lock, so this stub gives it that: every flock raises.
# On Linux the real module wins: this file sits first on PYTHONPATH there too, so it loads the interpreter's own fcntl in its place.
import os, sys
if os.name != 'nt':
    import importlib.machinery, importlib.util
    _here = os.path.dirname(os.path.abspath(__file__))
    _spec = importlib.machinery.PathFinder.find_spec('fcntl', [p for p in sys.path if os.path.abspath(p or '.') != _here])
    if _spec is None: raise ImportError('no fcntl module')
    _real = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_real)
    sys.modules[__name__] = _real
else:
    LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8

    def flock(fd, operation):
        raise OSError('flock is not available on Windows (win/pyshim/fcntl.py)')

    def lockf(fd, cmd, len=0, start=0, whence=0):
        raise OSError('lockf is not available on Windows (win/pyshim/fcntl.py)')

    def fcntl(fd, cmd, arg=0):
        raise OSError('fcntl is not available on Windows (win/pyshim/fcntl.py)')

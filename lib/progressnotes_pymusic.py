import e32
if e32.s60_version_info >= (3, 0):
    import imp
    _progressnotes = imp.load_dynamic('_progressnotes', '_progressnotes_pymusic.pyd')
else:
    import _progressnotes
del e32
del imp
from _progressnotes import *
del _progressnotes

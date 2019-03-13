import imp
_array = imp.load_dynamic("array", "_array_pymusic.pyd")

ArrayType = _array.ArrayType
__doc__ = _array.__doc__
__file__ = _array.__file__
__name__ = _array.__name__
array = _array.array
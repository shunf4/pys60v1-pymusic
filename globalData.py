import os

_data = {
    "localDataDir": os.path.abspath(r'.\data')
}

get = _data.__getitem__
set = _data.__setitem__
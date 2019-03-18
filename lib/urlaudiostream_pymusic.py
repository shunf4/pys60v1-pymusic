import imp
_urlaudiostream = imp.load_dynamic('urlaudiostream', '_urlaudiostream_pymusic.pyd')
import sys
sys.modules['urlaudiostream_pymusic'] = _urlaudiostream
import imp
_cfileman = imp.load_dynamic('cfileman', '_cfileman_pymusic.pyd')
import sys
sys.modules['cfileman_pymusic'] = _cfileman
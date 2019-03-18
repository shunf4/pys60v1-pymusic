import imp

try:
	cjson = imp.load_dynamic("cjson", "_cjson.dll")
except:
    cjson = imp.load_dynamic("cjson", "_cjson_pymusic.pyd")
    
import sys
sys.modules['testjson'] = cjson
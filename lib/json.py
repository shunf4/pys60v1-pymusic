import imp

try:
	cjson = imp.load_dynamic("cjson", "_cjson.dll")
except:
    cjson = imp.load_dynamic("cjson", "_cjson_pymusic.pyd")
    
def force_unicode_decode(str):
	return cjson.decode(str, True)
	
loads = force_unicode_decode
loads_donotdecode = cjson.decode
dumps = cjson.encode
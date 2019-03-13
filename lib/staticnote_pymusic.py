import imp
_staticnote = imp.load_dynamic('StaticNote', '_staticnote_pymusic.pyd')
about = _staticnote.about
linknote = _staticnote.linknote
note = _staticnote.note

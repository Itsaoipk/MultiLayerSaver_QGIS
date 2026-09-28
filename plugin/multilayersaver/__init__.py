def classFactory(iface):
    from .multilayer_saver_plugin import MultiLayerSaverPlugin
    return MultiLayerSaverPlugin(iface)

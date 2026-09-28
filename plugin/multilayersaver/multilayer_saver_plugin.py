"""MultiLayerSaver - Plugin-Einstiegspunkt.

Menueeintrag unter Erweiterungen -> MultiLayerSaver ->
"Temporaere Layer speichern".

Ablauf: Alle temporaren (Memory-)Layer anzeigen -> Auswahl per
Checkbox -> Format waehlen (Shapefiles + QML Standard, GeoPackage
optional) -> speichern und im Layerstack ersetzen.
"""

from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .auswahl_dialog import LayerAuswahlDialog
from .speicher_logik import speichern, temporaere_layer_sammeln


class MultiLayerSaverPlugin:

    def __init__(self, iface):
        self.iface = iface
        self.aktion = None

    def initGui(self):
        self.aktion = QAction(
            "Temporäre Layer speichern",
            self.iface.mainWindow()
        )
        self.aktion.triggered.connect(self.starten)

        self.iface.addPluginToMenu("MultiLayerSaver", self.aktion)
        self.iface.addToolBarIcon(self.aktion)

    def unload(self):
        if self.aktion:
            self.iface.removePluginMenu("MultiLayerSaver", self.aktion)
            self.iface.removeToolBarIcon(self.aktion)
            self.aktion = None

    def starten(self):

        try:
            ogr_paare = temporaere_layer_sammeln()

            auswahl, ziel, format_ = LayerAuswahlDialog.abfragen(
                ogr_paare
            )

            erfolgte, fehler = speichern(auswahl, ziel, format_)

        except Exception as abbruch:
            text = str(abbruch)
            if text not in ("Abbruch", "Keine temporären Layer vorhanden."):
                QMessageBox.critical(
                    None,
                    "MultiLayerSaver",
                    text
                )
            return

        self._ergebnis_zeigen(erfolgte, fehler, ziel, format_)

    def _ergebnis_zeigen(self, erfolgte, fehler, ziel, format_):

        if not erfolgte and not fehler:
            return

        if format_ == "shapefile":
            ziel_text = "Zielordner:\n{}".format(ziel)
        else:
            ziel_text = "GeoPackage:\n{}".format(ziel)

        meldung = ""

        if erfolgte:
            meldung += (
                "{} Layer gespeichert und im Layerstack ersetzt "
                "(Styling und Beschriftung übernommen):\n"
                " - {}\n\n".format(
                    len(erfolgte), "\n - ".join(erfolgte)
                )
            )

        if fehler:
            meldung += (
                "Fehler bei {} Layer(n):\n - {}\n\n".format(
                    len(fehler), "\n - ".join(fehler)
                )
            )

        meldung += ziel_text

        if fehler and not erfolgte:
            box = QMessageBox.critical
        elif fehler:
            box = QMessageBox.warning
        else:
            box = QMessageBox.information

        box(None, "MultiLayerSaver", meldung)

"""MultiLayerSaver - Dialog zur Auswahl der zu speichernden Layer.

Zeigt alle temporaren (Memory-)Layer des Projekts mit Checkboxen,
laesst Zielordner und Format waehlen und gibt die Auswahl zurueck.
"""

import os

from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout
)


class LayerAuswahlDialog:
    """Statischer Dialog: Layer-Auswahl, Zielordner, Format."""

    FORMAT_SHAPEFILE = "shapefile"
    FORMAT_GEOPACKAGE = "geopackage"

    @staticmethod
    def abfragen(ogr_paare):
        """Liefert (auswahl, ziel, format) oder wirft Exception bei Abbruch.

        ogr_paare: Liste von (layer_tree_node, vektorlayer) fuer alle
        temporaren Layer im Projekt.
        """

        dialog = QDialog(None)
        dialog.setWindowTitle("MultiLayerSaver - Layer speichern")

        layout = QVBoxLayout(dialog)

        if not ogr_paare:
            layout.addWidget(QLabel(
                "Keine temporären Layer im Projekt gefunden.\n"
                "Temporäre Layer entstehen z. B. durch den "
                "ProfilKoordinatensystem- oder den Ortho-Import."
            ))
            button = QDialogButtonBox(
                QDialogButtonBox.Close,
                parent=dialog
            )
            button.accepted.connect(dialog.accept)
            button.rejected.connect(dialog.reject)
            layout.addWidget(button)
            dialog.exec_()
            raise Exception("Keine temporären Layer vorhanden.")

        layer_box = QGroupBox("Temporäre Layer (alle gefundenen):")
        layer_layout = QGridLayout(layer_box)

        checkboxen = []
        for zeile, (knoten, layer) in enumerate(ogr_paare):
            box = QCheckBox(layer.name())
            box.setChecked(True)
            layer_layout.addWidget(box, zeile, 0)
            info = QLabel("{} Features".format(layer.featureCount()))
            layer_layout.addWidget(info, zeile, 1)
            checkboxen.append((box, knoten, layer))

        layout.addWidget(layer_box)

        ziel_box = QGroupBox("Ziel:")
        ziel_layout = QGridLayout(ziel_box)

        ziel_layout.addWidget(QLabel("Ordner (Shapefiles):"), 0, 0)
        ordner_feld = QLineEdit(os.path.expanduser("~"))
        ziel_layout.addWidget(ordner_feld, 0, 1)
        ordner_button = QPushButton("...")
        ordner_button.clicked.connect(
            lambda: LayerAuswahlDialog._ordner_waehlen(ordner_feld)
        )
        ziel_layout.addWidget(ordner_button, 0, 2)

        ziel_layout.addWidget(QLabel("GeoPackage-Datei:"), 1, 0)
        gpkg_feld = QLineEdit(
            os.path.join(
                os.path.expanduser("~"), "layers.gpkg"
            )
        )
        ziel_layout.addWidget(gpkg_feld, 1, 1)
        gpkg_button = QPushButton("...")
        gpkg_button.clicked.connect(
            lambda: LayerAuswahlDialog._datei_waehlen(gpkg_feld)
        )
        ziel_layout.addWidget(gpkg_button, 1, 2)

        layout.addWidget(ziel_box)

        format_box = QGroupBox("Format:")
        format_layout = QVBoxLayout(format_box)

        shape_radio = QRadioButton(
            "Shapefiles + QML-Stildateien (Standard; .shp pro Layer, "
            "Styling und Beschriftung liegen als .qml daneben)"
        )
        shape_radio.setChecked(True)
        format_layout.addWidget(shape_radio)

        gpkg_radio = QRadioButton(
            "GeoPackage (alle Layer in einer Datei)"
        )
        format_layout.addWidget(gpkg_radio)

        layout.addWidget(format_box)

        button = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            parent=dialog
        )
        button.accepted.connect(dialog.accept)
        button.rejected.connect(dialog.reject)
        layout.addWidget(button)

        dialog.resize(560, 520)

        if dialog.exec_() != QDialog.Accepted:
            raise Exception("Abbruch")

        auswahl = [
            (knoten, layer)
            for box, knoten, layer in checkboxen
            if box.isChecked()
        ]
        if not auswahl:
            raise Exception("Kein Layer ausgewählt.")

        if shape_radio.isChecked():
            format_ = LayerAuswahlDialog.FORMAT_SHAPEFILE
            ziel = ordner_feld.text().strip()
            if not ziel:
                raise Exception("Kein Zielordner gewählt.")
            if not os.path.isdir(ziel):
                raise Exception(
                    "Zielordner existiert nicht:\n{}".format(ziel)
                )
        else:
            format_ = LayerAuswahlDialog.FORMAT_GEOPACKAGE
            ziel = gpkg_feld.text().strip()
            if not ziel:
                raise Exception("Keine GeoPackage-Datei gewählt.")
            if not ziel.lower().endswith(".gpkg"):
                ziel += ".gpkg"

        return auswahl, ziel, format_

    @staticmethod
    def _ordner_waehlen(feld):
        ordner = QFileDialog.getExistingDirectory(
            None,
            "Zielordner für Shapefiles wählen",
            feld.text().strip() or ""
        )
        if ordner:
            feld.setText(ordner)

    @staticmethod
    def _datei_waehlen(feld):
        pfad, _ = QFileDialog.getSaveFileName(
            None,
            "GeoPackage-Datei wählen",
            feld.text().strip() or "",
            "GeoPackage (*.gpkg)"
        )
        if pfad:
            feld.setText(pfad)

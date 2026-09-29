"""MultiLayerSaver - Kernlogik.

Speichert temporare (Memory-)Layer als Shapefiles (Standard, mit
QML-Stildatei inklusive Labeling) oder als GeoPackage und ersetzt
die temporaren Layer an derselben Stelle im Layerstack.

Fehler werden pro Layer sauber diagnostiziert: Datei existiert?
Layer ladet und ist valide? Die Meldung nennt Pfad und Ursache.
"""

import os
import re

from qgis.core import (
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsLayerTreeLayer
)

SHP_ERWEITERUNGEN = (".shp", ".shx", ".dbf", ".prj", ".qml")


def temporaere_layer_sammeln():
    """Alle Memory-Vektorlayer des Projekts samt Layer-Tree-Knoten."""

    ergebnis = []
    root = QgsProject.instance().layerTreeRoot()

    for knoten in root.findLayers():
        layer = knoten.layer()
        if not isinstance(layer, QgsVectorLayer):
            continue
        if layer.providerType() != "memory":
            continue
        ergebnis.append((knoten, layer))

    return ergebnis


def dateiname_bereinigen(name):
    """Layername als dateisystemtauglichen Basisnamen wandeln."""

    bereinigt = re.sub(r"[^\w .-]", "_", name, flags=re.UNICODE).strip()
    return bereinigt or "layer"


def _shapefile_pfade(ordner, layer_name):
    basis = os.path.join(ordner, dateiname_bereinigen(layer_name))
    return basis, basis + ".shp"


def _gpkg_layername(name):
    """Layername fuer GeoPackage (Leerzeichen sind unproblematisch)."""

    return re.sub(r"[^\w .-]", "_", name, flags=re.UNICODE) or "layer"


def _schreiboptionen(format_, ziel, index, layer_name):
    """SaveVectorOptions je Format und Position."""

    optionen = QgsVectorFileWriter.SaveVectorOptions()
    optionen.fileEncoding = "UTF-8"

    if format_ == "geopackage":
        optionen.driverName = "GPKG"
        optionen.layerName = _gpkg_layername(layer_name)
        if index == 0:
            optionen.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteFile
            )
        else:
            optionen.actionOnExistingFile = (
                QgsVectorFileWriter.CreateOrOverwriteLayer
            )
    else:
        optionen.driverName = "ESRI Shapefile"

    return optionen


def _vektor_schreiben(layer, pfad, optionen):
    """Schreibt den Layer; robust gegen QGIS-API-Varianten.

    Rueckgabe (erfolg: bool, fehlermeldung: str oder None).
    """

    try:
        fehler, meldung, _, _ = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer, pfad,
            QgsProject.instance().transformContext(),
            optionen
        )
    except TypeError:
        try:
            fehler, meldung, _, _ = (
                QgsVectorFileWriter.writeAsVectorFormatV3(
                    layer, pfad, optionen
                )
                )
        except TypeError:
            return False, (
                "QGIS-API nicht kompatibel "
                "(writeAsVectorFormatV3 nicht aufrufbar). "
                "Bitte QGIS-Version melden."
            )

    if fehler != QgsVectorFileWriter.NoError:
        return False, str(meldung or "unbekannter Schreibfehler")

    return True, None


def _shapefiles_loeschen(ordner, layer_name):
    """Alte Dateien eines Layers entfernen (fuer saubere Ueberschreibung)."""

    basis, _ = _shapefile_pfade(ordner, layer_name)
    for endung in SHP_ERWEITERUNGEN:
        pfad = basis + endung
        if os.path.exists(pfad):
            try:
                os.remove(pfad)
            except OSError:
                pass


def _shapefile_speichern(layer, ordner):
    """Layer als Shapefile schreiben; Rueckgabe (pfad, fehlermeldung)."""

    basis, shp_pfad = _shapefile_pfade(ordner, layer.name())
    _shapefiles_loeschen(ordner, layer.name())

    optionen = _schreiboptionen("shapefile", ordner, 0, layer.name())
    erfolg, meldung = _vektor_schreiben(layer, shp_pfad, optionen)

    if not erfolg:
        return None, meldung

    if not os.path.exists(shp_pfad):
        return None, (
            "Datei wurde nicht erzeugt: {}".format(shp_pfad)
        )

    return shp_pfad, None


def _gpkg_speichern(layer, gpkg_pfad, index):
    """Layer ins GeoPackage schreiben; Rueckgabe (fehlermeldung)."""

    optionen = _schreiboptionen("geopackage", gpkg_pfad, index, layer.name())
    erfolg, meldung = _vektor_schreiben(layer, gpkg_pfad, optionen)
    if not erfolg:
        return meldung
    if not os.path.exists(gpkg_pfad):
        return "Datei wurde nicht erzeugt: {}".format(gpkg_pfad)
    return None


def _qml_pfad_fuer(format_, ziel, shp_pfad, name):
    """QML-Stildatei-Pfad je Format bestimmen.

    Shapefile: QML liegt neben der .shp (gleicher Basisname).
    GeoPackage: QMLs liegen im Unterordner 'styles' neben der .gpkg,
    Dateiname vom ORIGINALEN Layernamen abgeleitet (der geladene
    Layer heisst wieder Original-Name, nicht der bereinigte
    Tabellenname).
    """

    if format_ == "geopackage":
        ordner = os.path.join(
            os.path.dirname(ziel) or ".", "styles"
        )
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError as ausnahme:
            return None, (
                "Stilordner konnte nicht angelegt werden: {}".format(
                    ausnahme
                )
            )
        basis = os.path.join(ordner, dateiname_bereinigen(name))
        return basis + ".qml", None

    return os.path.splitext(shp_pfad)[0] + ".qml", None


def _stil_speichern(layer, qml_pfad):
    """QML-Stildatei schreiben (inkl. Labeling)."""

    try:
        ergebnis = layer.saveNamedStyle(qml_pfad)
    except Exception as ausnahme:
        return "Stil konnte nicht gespeichert werden: {}".format(
            ausnahme
        )

    erfolg = False
    if isinstance(ergebnis, (tuple, list)):
        erfolg = bool(ergebnis[-1]) if len(ergebnis) > 1 else False
    else:
        erfolg = bool(ergebnis)

    if not erfolg:
        detail = ergebnis if isinstance(ergebnis, str) else str(ergebnis)
        return "Stil konnte nicht gespeichert werden: {}".format(
            detail
        )

    if not os.path.exists(qml_pfad):
        return "QML-Stildatei fehlt: {}".format(qml_pfad)

    return None


def _gespeicherten_laden(shp_pfad, gpkg_pfad, gpkg_layername, name):
    """Gespeicherten Layer laden; Rueckgabe (layer, fehlermeldung)."""

    if shp_pfad is not None:
        ziel = QgsVectorLayer(shp_pfad, name, "ogr")
    else:
        uri = "{}|layername={}".format(gpkg_pfad, gpkg_layername)
        ziel = QgsVectorLayer(uri, name, "ogr")

    if not ziel.isValid():
        detail = shp_pfad or "{} (Layer: {})".format(
            gpkg_pfad, gpkg_layername
        )
        return None, "Gespeicherter Layer ist ungültig: {}".format(detail)

    return ziel, None


def _stil_laden(ziel, qml_pfad):
    """QML-Stil auf den geladenen Layer anwenden (falls vorhanden)."""

    if qml_pfad is None:
        return
    if not os.path.exists(qml_pfad):
        return
    try:
        ziel.loadNamedStyle(qml_pfad)
    except Exception:
        pass


def _im_layerstack_ersetzen(knoten, ziel):
    """Temporaeren Layer im Layerstack durch den gespeicherten ersetzen.

    Der neue Layer erhaelt Position und Gruppe des alten Layers.
    """

    parent = knoten.parent()
    if parent is None:
        QgsProject.instance().addMapLayer(ziel)
        return

    alte_id = knoten.layerId()

    position = 0
    kinder = parent.children()
    for index, kind in enumerate(kinder):
        if kind is knoten:
            position = index
            break
    else:
        position = len(kinder)

    QgsProject.instance().addMapLayer(ziel, False)
    parent.insertChildNode(position, QgsLayerTreeLayer(ziel))

    QgsProject.instance().removeMapLayer(alte_id)


def speichern(auswahl, ziel, format_):
    """Haupteinstieg: Auswahl speichern und Layerstack aktualisieren.

    Rueckgabe (erfolgte: list[str], fehler: list[str]).
    """

    erfolgte = []
    fehler = []

    gpkg_index = 0

    for knoten, layer in auswahl:

        name = layer.name()

        shp_pfad = None
        meldung = None

        if format_ == "shapefile":
            shp_pfad, meldung = _shapefile_speichern(layer, ziel)
        else:
            meldung = _gpkg_speichern(layer, ziel, gpkg_index)
            gpkg_index += 1

        if meldung:
            fehler.append("{}: {}".format(name, meldung))
            continue

        qml_pfad, meldung = _qml_pfad_fuer(
            format_, ziel, shp_pfad, name
        )
        if meldung:
            fehler.append("{}: {}".format(name, meldung))
            continue

        qml_meldung = _stil_speichern(layer, qml_pfad)
        if qml_meldung:
            fehler.append("{}: {}".format(name, qml_meldung))
            continue

        gpkg_layername = (
            _gpkg_layername(name) if format_ == "geopackage"
            else None
        )
        ziel_layer, meldung = _gespeicherten_laden(
            shp_pfad, ziel, gpkg_layername, name
        )

        if meldung:
            fehler.append("{}: {}".format(name, meldung))
            continue

        _stil_laden(ziel_layer, qml_pfad)

        erfolgte.append(name)
        _im_layerstack_ersetzen(knoten, ziel_layer)

    return erfolgte, fehler

# MultiLayerSaver (QGIS-Plugin)

Speichert mehrere temporäre (Memory-)Layer **gleichzeitig und inklusive
Styling und Beschriftung** dauerhaft ab und ersetzt sie an derselben
Stelle im Layerstack. Entwickelt für die Layer der Plugins
[ProfilKoordinatensystem](https://github.com/Itsaoipk/profil-koordinatenraster-qgis)
und [Profil_Ortho_Import](https://github.com/Itsaoipk/asbuilt-orthobild-import-qgis),
funktioniert aber mit allen temporären Layern im Projekt.

## Problem, das das Plugin löst

- QGIS-eigene/andere Batch-Saver speichern nur die Daten, aber **nie
  Renderer und Labeling** – Beschriftungen gehen verloren.
- Gespeicherte Layer tauchen nicht im Layerstack auf, die temporären
  Layer bleiben stehen.

MultiLayerSaver schreibt pro Layer zusätzlich eine **QML-Stildatei**
und wendet sie sofort wieder an: Die Karte sieht nach dem Speichern
exakt identisch aus.

## Formate

| Format | Standard | Beschreibung |
|---|---|---|
| **Shapefiles + QML** | ✅ | `.shp` pro Layer, Styling + Labeling als `.qml` daneben. Weitergabe-freundlich (z. B. Landesdenkmalpflege). |
| GeoPackage | optional | Alle Layer in einer `.gpkg`. |

## Versionshistorie

- **v0.2.0** – **Toolbar-Button mit eigenem SVG-Icon:** "Temporäre Layer speichern" zeigt in der QGIS-Werkzeugleiste jetzt ein eigenes Icon (drei gestapelte Layer-Rauten – der Layerstack – mit grüner Diskette als Speichern-Symbol, `icon.svg`); gilt via `metadata.txt` auch als Plugin-Symbol im Erweiterungs-Dialog. Tooltip beim Hovern. Der Toolbar-Button war bereits vorhanden, hatte bisher aber nur ein Text-Label. Menüeintrag bleibt parallel bestehen.

## Bedienung

1. **Erweiterungen → MultiLayerSaver → „Temporäre Layer speichern"**
2. Im Dialog: Layer per Checkbox abwählen, Zielordner wählen, Format belassen (Shapefile) oder umschalten
3. Speichern – die temporären Layer werden im Layerstack durch die gespeicherten ersetzt

## Fehlerdiagnose

Jeder Layer wird einzeln geprüft: Wurde die Datei erzeugt? Lässt sich
der gespeicherte Layer laden und ist er valide? Bei Problemen erscheint
eine Meldung mit **Dateipfad und Ursache** pro Layer – der Rest wird
trotzdem gespeichert.

## Installation

Ordner `plugin/multilayersaver` nach
`<QGIS-Profil>/python/plugins/multilayersaver` kopieren und in QGIS
aktivieren.

## Struktur

```
plugin/multilayersaver/
├── __init__.py                 # classFactory
├── metadata.txt
├── auswahl_dialog.py            # Layer-Auswahl, Ziel, Format
├── speicher_logik.py            # Schreiben, QML, Layerstack-Ersetzung
└── multilayer_saver_plugin.py   # Menü + Ablauf
```

## Grenzen von Shapefiles (bekannt und unkritisch hier)

- Feldnamen max. 10 Zeichen (ggf. Kürzung durch QGIS/GDAL)
- ein Geometrietyp pro Layer
- Umlaute in Feldnamen werden beim Export ggf. angepasst

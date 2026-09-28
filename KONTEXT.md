# MultiLayerSaver_QGIS – Projektkontext

**Stand: 28.09.2026 – v0.1.0 funktioniert im Test (Owner-bestätigt)**

Dieses Dokument sichert den Projektverlauf aus dem Entwicklungs-Chat,
damit die Arbeit angesetzt werden kann, wenn der Chat verloren geht.

## Zweck des Plugins

Speichert **mehrere temporäre (Memory-)Layer gleichzeitig und inklusive
Styling und Beschriftung** dauerhaft ab und ersetzt sie an derselben
Stelle im Layerstack. Entwickelt für die Layer der Plugins:

- **ProfilKoordinatensystem** –
  https://github.com/Itsaoipk/profil-koordinatenraster-qgis
- **Profil_Ortho_Import** –
  https://github.com/Itsaoipk/asbuilt-orthobild-import-qgis

Funktioniert aber mit allen Memory-Layern im QGIS-Projekt.

## Warum dieses Plugin existiert (Problemgeschichte)

1. Die beiden Import-Plugins erzeugen viele temporäre Layer
   (Achsen, Ticks, Kreuze, X_/Y_Beschriftung, Passpunkte, Aufmaß Profil …).
2. QGIS-Batch-Saver (z. B. VectorBatchSaver) speichern nur die **Daten**,
   nie Renderer und Labeling → Beschriftungen gehen verloren; gespeicherte
   Layer tauchen nicht im Layerstack auf.
3. Erster Versuch: Speicherfunktion **in** die Plugins einbauen
   (PR #33 im Raster-Repo, PR #37 im Ortho-Repo). Scheiterte in QGIS mit
   „Gespeicherter Layer konnte nicht geladen werden" (GeoPackage-Layer
   luden nicht).
4. **Entscheidung des Owners:** Plugins schlank halten, Speichern als
   **eigenständiges Plugin**. Die eingebauten Funktionen wurden reverted:
   - Raster-Repo: PR #34 (Revert, gemerged)
   - Ortho-Repo: PR #38 (Revert, gemerged)
5. Neues Repo angelegt (dieses), Plugin von Grund auf gebaut – getestet
   und funktionsfähig.

## Architektur

```
plugin/multilayersaver/
├── __init__.py                 # classFactory
├── metadata.txt                # v0.1.0, QGIS ≥ 3.16
├── auswahl_dialog.py           # Dialog: Checkboxen je Layer,
│                               #   Zielordner, Formatwahl
├── speicher_logik.py          # Kern (siehe unten)
└── multilayer_saver_plugin.py  # Menüeintrag + Ablauf + Ergebnismeldung
```

### Bedienung
Erweiterungen → MultiLayerSaver → „Temporäre Layer speichern" →
Layer (alle vorausgewählt) prüfen, Zielordner wählen, Format belassen
(Shapefile+QML) oder GeoPackage wählen → OK.

### Formate
- **Shapefiles + QML (Standard):** `.shp` pro Layer, Styling + komplettes
  Labeling als `.qml` daneben. Weitergabe-freundlich (Owner übergibt
  Shapefiles ggf. an die Landesdenkmalpflege; GeoPackage macht bei ihm
  öfter Probleme).
- **GeoPackage (optional):** alle Layer in einer `.gpkg`.

## Kernlogik (speicher_logik.py) – Ablauf pro Layer

1. Memory-Layer sammeln (Layer-Tree-Knoten + Layer je `findLayers()`,
   Filter `providerType() == "memory"`)
2. Shapefile schreiben (`writeAsVectorFormatV3`, mit Fallback für
   QGIS-API-Varianten)
3. QML-Stil schreiben: `layer.saveNamedStyle(qml_pfad)`
4. Gespeicherten Layer laden (`QgsVectorLayer(..., "ogr")`),
   `isValid()` prüfen
5. QML auf geladenen Layer anwenden (`loadNamedStyle`)
6. Im Layerstack ersetzen: neue Layer-Tree-Node an derselben Position
   in dieselbe Gruppe, danach `removeMapLayer(alte_id)`

## Behobene Bugs (wichtig fürs Verständnis des Codes!)

1. **Erfolgsmeldung als Fehler gewertet:**
   `saveNamedStyle()` liefert `(meldung, erfolg)`. Der Meldungstext
   („Vorgabestildatei als … gespeichert") wurde fälschlich als Fehler
   interpretiert → Abbruch vor der Layerstack-Ersetzung.
   Fix: Erfolg-Flag (`ergebnis[-1]`) auswerten + QML auf Existenz prüfen.
2. **Use-after-free beim Ersetzen:**
   Nach `removeMapLayer()` löscht QGIS sofort das C++-Objekt des
   Memory-Layers. Ein Zugriff auf `layer.name()` danach crashte mit
   „wrapped C/C++ object of type QgsVectorLayer has been deleted".
   Fix (3 Änderungen):
   - `name = layer.name()` einmal am Schleifenanfang cachen
   - `erfolgte.append(name)` VOR der Layerstack-Ersetzung
   - In `_im_layerstack_ersetzen`: `knoten.layerId()` statt
     `knoten.layer().id()` (kein Zugriff auf das Layer-Objekt)

## Commits (main)

- `d5a7a4e` – Plugin-Grundstruktur v0.1.0
- `7104f15` – Fix: Erfolgsmeldung von saveNamedStyle nicht als Fehler
- `3771bd4` – Fix: Use-after-free beim Layerstack-Ersetzen

## Sandbox-/GitHub-Besonderheiten (falls Agent wieder ansetzt)

- Git-HTTPS-Push und REST-API für **neue/gelegentliche Repos** schlagen
  in der Sandbox fehl (401/„Repository not found"), obwohl `gh repo list`
  die Repos zeigt und GET auf `/user/repos` volle Rechte meldet.
- **Zuverlässiger Weg: GraphQL-API** mit `createCommitOnBranch`
  (Dateien base64-kodiert als `fileChanges.additions`):
  1. HEAD-OID holen: `repository.defaultBranchRef.target.oid`
  2. Mutation `createCommitOnBranch` mit `branch.repositoryNameWithOwner`
     + `branchName`, `expectedHeadOid` = HEAD-OID
- **Bei leeren Repos** funktioniert das nicht → Owner muss zuerst per
  Web-UI eine README.md anlegen („Add a README file"), dann klappt es.
- Revert-PRs: Raster-Repo #34 gemerged; Ortho-Repo PR #38: Branch
  `vibe/revert-speichern-07e5df` wurde ebenfalls via GraphQL-Commit
  erstellt und gemerged.

## Offene Ideen (Owner hat noch nicht entschieden)

- Zielordner in QGIS-Einstellungen merken
- „Alle auswählen/keine"-Buttons im Dialog
- Temp-Layer optional nur ausblenden statt ersetzen
- Plugin-Icon für die Toolbar

## Grenzen von Shapefiles (Dokumentation für Nutzer)

- Feldnamen max. 10 Zeichen
- ein Geometrietyp pro Layer
- Umlaute in Feldnamen werden ggf. angepasst

# MultiLayerSaver_QGIS – Projektkontext

**Stand: 28.09.2026 – v0.1.0 funktioniert im Test (Owner-bestätigt)**

> ~~**OFFENER PUNKT: Bug GeoPackage-Modus**~~ → **ERLEDIGT 29.09.2026**
> (Commit `04d7f52`, siehe "ERLEDIGT: GeoPackage-Stil-Fix")

Dieses Dokument sichert den Projektverlauf aus dem Entwicklungs-Chat,
damit die Arbeit angesetzt werden kann, wenn der Chat verloren geht.

## ERLEDIGT: GeoPackage-Stil-Fix (29.09.2026, Commit 04d7f52)

**Fix umgesetzt wie geplant:** Neue Funktion `_qml_pfad_fuer(format_, ziel,
shp_pfad, name)` bestimmt den QML-Pfad je Format: Shapefile → neben der
.shp; GeoPackage → Unterordner `styles/` neben der .gpkg, Dateiname vom
ORIGINALEN Layernamen (nicht Tabellenname). `_stil_speichern` und
`_stil_laden` arbeiten generisch auf dem QML-Pfad und laufen jetzt in
BEIDEN Formaten. Dialog-Beschreibung erweitert.
**Status: wartet auf Owner-Test in QGIS.**

**Gemeldet von Owner (28.09.2026):** Wählt man im Dialog **GeoPackage**
als Format, werden Stile und Beschriftungen NICHT auf die gespeicherten
Layer übernommen. (Shapefile+QML-Modus funktioniert seit Fix `3771bd4`
sauber – Owner bestätigt.)

**Ursache (per Code-Analyse gefunden, in `speicher_logik.py`):**
Die Stil-Funktionen laufen nur im Shapefile-Pfad:

```python
if shp_pfad is not None:            # nur bei Shapefile gesetzt!
    qml_meldung = _stil_speichern(layer, shp_pfad)   # Zeile ~277
...
if shp_pfad is not None:
    _stil_laden(ziel_layer, shp_pfad)                # Zeile ~296
```

Im GeoPackage-Modus ist `shp_pfad` immer `None` → QML wird weder
fuer den Quell-Layer geschrieben noch auf den geladenen Ziel-Layer
angewendet. GeoPackage selbst speichert die Stile NICHT im File,
QGIS liest sie auch nicht automatisch → alle Layer erscheinen im
Default-Stil ohne Labeling.

**Ursprünglicher Fixplan (der Umsetzung zugrunde gelegen):**
1. QML-Datei je Layer schreiben – im GeoPackage-Modus Unterordner
   `styles/` neben der .gpkg → umgesetzt via `_qml_pfad_fuer()`
2. `_gespeicherten_laden()` – QML-Pfad zentral in `speichern()`
   bestimmen → umgesetzt
3. `_stil_laden(ziel_layer, qml_pfad)` in beiden Modi aufrufen →
   umgesetzt (`if qml_pfad is not None`-Logik, kein `shp_pfad`-Check
   mehr fürs Styling)
4. QML-Dateiname vom ORIGINAL-Layernamen ableiten → umgesetzt
   (`dateiname_bereinigen(name)` im styles/-Ordner)
5. Test beider Formate → **offen, Owner testet**

**Alternative (verworfen):** `saveStyleToDatabase()` – projektgebunden,
nicht portabel. QML-Dateien sind die bessere Lösung (mit .gpkg
zusammen weitergebbar).

**Zusätzlich gemeldet/geplant (siehe unten 'Offene Ideen'):**
- Zielordner in QGIS-Einstellungen merken
- „Alle auswählen/keine"-Buttons
- Temp-Layer optional ausblenden
- Plugin-Icon

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

## FAQ: "Hey, wie war das nochmal mit QML, Shapefile und dem Kram?"

**Für alle, die es kurz brauchen (Dummies-Erklärung, bitte erhalten!):**

### Was ist ein Shapefile?
Keine einzelne Datei, sondern ein Satz von mindestens 4 Dateien,
die zusammengehören (QGIS zeigt sie als eine an):
```
Achsen.shp  -> Geometrie (WO ist die Linie)
Achsen.shx  -> Index (wo steht was in der .shp)
Achsen.dbf  -> Attributtabelle (WAS ist es: Typ, Laenge)
Achsen.prj  -> Koordinatensystem
```
Vorteile: Ur-Standard, JEDE Software liest es (ArcGIS, CAD,
Landesdenkmalpflege...). Nachteile: 4+ Dateien, Feldnamen max.
10 Zeichen, Umlaute boesen, nur ein Geometrietyp pro Layer.

### Was ist ein GeoPackage?
EINE einzige .gpkg-Datei (= kleine SQLite-Datenbank), in der alle
Layer stecken. Vorteile: eine Datei fuer alles, laengere Feldnamen,
mehrere Layer. Nachteile: juengeres Format, aeltere Systeme koennen
es evtl. nicht lesen (und Owner hatte schon Probleme damit).
Merksatz: Shapefile = Mappe mit losen Blaettern (jeder kann lesen,
Blaetter koennen fehlen). GeoPackage = Schnellhefter mit allem
zusammen.

### Was ist QML?
Die "Frisier-Anweisung" fuer einen Layer: Farbe, Linienbreite,
Schriftgroesse, wo die Beschriftungen sitzen. Die .shp sagt WO etwas
ist - die QML sagt, WIE es aussieht.
WICHTIG: Shapefiles koennen KEIN Styling speichern (1980er-Format).
Deshalb liegt die QML NEBEN den Daten (gleicher Basisname):
```
Achsen.shp   <- Daten
Achsen.qml   <- Stil/Labeling-Anweisung
```
(Fussnote: QML heisst hier "QGIS Markup Language" - hat NICHTS mit
der Qt-Programmiersprache QML zu tun.)

### Woher weiss ein Shapefile, wie es aussieht?
Es WEISS ES NICHT. QGIS muss sich den Stil woanders holen:
1. aus dem Projekt-Protokoll (.qgz/.qgs) - Normalfall
2. aus einer QML-Datei neben den Daten
3. aus der persoenlichen Stildatenbank (qgis.db im Profil)
4. sonst: Zufalls-Default-Stil (bunt, ohne Labeling)

### Wie macht QGIS das ohne unser Plugin?
Ueber das PROJEKT: Die .qgs/.qgz speichert fuer jeden Layer die
komplette Stil-Anweisung. Deshalb sieht gespeichertes Projekt immer
gleich aus. ABER: Projekt weg = Stil weg. Fuer Weitergabe
(Landesdenkmalpflege, Kollegen, Archiv) braucht es die QML neben
den Daten - genau das schreibt unser Plugin automatisch.

### Warum ging GeoPackage-Stil verloren (der Bug von 29.09.)?
Eine .gpkg IST eine Datenbank. QGIS behandelt sie wie eine DB-
Verbindung: loadNamedStyle(pfad) suchte zuerst einen Stil IN der
Datenbank statt die QML-Datei zu lesen -> Layer kamen im Default-
Stil ohne Labeling. Fix laut qgis/QGIS#54515:
`loadNamedStyle(qml_pfad, True)` - das True erzwingt das Laden aus
der DATEI. Zusaetzlich setLabelsEnabled(quelle.labelsEnabled())
und triggerRepaint().

### WTF ist ein AST-Check?
Der Computer "liest" den Code vor dem Upload und prueft seine
Struktur (z.B.: wird die neue Funktion ueberall mit 4 Argumenten
aufgerufen?). py_compile = Rechtschreibpruefung (Klammern...),
AST = Logik-Trockentest. QGIS laeuft in der Sandbox nicht, deshalb
ist der Owner-Test in QGIS der wahre Pruefstand.

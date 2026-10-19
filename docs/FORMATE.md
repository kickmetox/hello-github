# Formate

Andreas Meyer, ame@sellerbach.de

`.pptx` ist PresentationML nach ECMA-376 und ISO/IEC 29500. `.ppt` ist das binäre Format nach [MS-PPT], verpackt in einem OLE-Container nach [MS-CFB]. Der Leser steht in `src/officedisplay/io/pptx_io.py` und `src/officedisplay/io/ppt_binary.py`.

## PPTX

Gelesen wird das Paket `ppt/presentation.xml` mit den Folien darunter.

- Die Foliengröße ist `p:sldSz`, Attribute `cx` und `cy`, in EMU. 914400 EMU sind ein Zoll. Fehlt das Element, gelten 12192000 × 6858000 EMU, also 13,333 × 7,5 Zoll. [MS-OE376] 2.1.1143 verweist auf Part 4 Section 4.3.1.34.
- Lage und Größe kommen aus DrawingML `a:xfrm` (`a:off`, `a:ext`), geteilt durch diese Foliengröße. Gruppenkinder werden über `a:chOff` und `a:chExt` in Folienkoordinaten umgerechnet.
- Ein Bild ist `a:blip` mit `r:embed`. Die Beziehung zeigt auf das Bildteil, meist unter `ppt/media`.
- Der Hintergrund ist `p:bg` der Folie, sonst der des Folienlayouts, sonst der des Folienmasters. Eine Bildfüllung wird zum Hintergrundbild, eine Farbfüllung zur Hintergrundfarbe. Deckkraft kommt aus `a:alpha` oder `a:alphaModFix`, wenn vorhanden.
- Die Schriftgröße ist `a:rPr` oder `a:defRPr`, Attribut `sz`, in Hundertstel Punkt. Absätze bleiben Zeilen. Die Ausrichtung ist `l`, `ctr` oder `r`, die vertikale Ausrichtung kommt aus `a:bodyPr`.

Mit ankommen Text, einfache Formen mit Füllung und Umriss, Tabellen als Text und die Sprechernotiz.

Nicht gelesen werden SmartArt, Diagramme, Animationen und OLE-Objekte. Steht in so einem Rahmen noch Text, kann der Text ankommen, das Objekt selbst nicht. Zeichenpfade und 3D-Körper werden nicht nachgebaut.

`.pptx`, `.potx` und `.ppsx` sind derselbe PresentationML-Inhalt. `.pdrx`, `.prdx`, `.prsx`, `.prvx` und `.rtx` ebenfalls, wenn die Datei ein ZIP mit `ppt/presentation.xml` ist. Eine `.rtx` ohne dieses Paket wird als Text oder RTF zu Folien.

## PPT

[MS-CFB] 2.2 ist der Compound-File-Header. Daraus kommen die Ströme, darunter `PowerPoint Document`. [MS-PPT] 2.3.1 ist der RecordHeader (`recVer`/`recInstance`, `recType`, `recLen`).

Folien sind `RT_Slide` `0x03EE`. Text steht in `RT_TextCharsAtom` `0x0FA0` ([MS-PPT] 2.9.42, UTF-16LE) und `RT_TextBytesAtom` `0x0FA8` ([MS-PPT] 2.9.43, Windows-1252). Die Nummern stehen in [MS-PPT] 2.13.24. Hat die Folie selbst keinen Text, wird die Gliederung aus `RT_SlideListWithText` `0x0FF0` und `RT_SlidePersistAtom` `0x03F3` genommen.

Bilder nur, wenn im Folienkörper oder im Pictures-Strom die Signatur von PNG oder JPEG steht. So liegen diese OfficeArt-Blips im Strom. Andere Blips und freie Zeichnungen bleiben weg.

LibreOffice ist nicht vorausgesetzt. Ist `soffice` schon installiert, darf es die Datei vorher nach PPTX wandeln. Sonst liest der OLE-Leser.

Nicht gelesen werden freie Zeichnungen im alten PPT, Animationen, OLE und SmartArt. Die ursprüngliche Zeichenposition aus dem OfficeArt-Baum wird nicht rekonstruiert. Text und gefundene Bilder liegen auf festen Flächen der Folie.

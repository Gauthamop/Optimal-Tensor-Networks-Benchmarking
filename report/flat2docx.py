"""Convert a Word flat-OPC XML export (Range.WordOpenXML) into a .docx package."""
import base64
import sys
import zipfile
from pathlib import Path

from lxml import etree

PKG = 'http://schemas.microsoft.com/office/2006/xmlPackage'
REL_TYPE = 'application/vnd.openxmlformats-package.relationships+xml'


def convert(flat, out):
    root = etree.fromstring(Path(flat).read_bytes())
    parts, overrides = [], []
    for part in root.findall(f'{{{PKG}}}part'):
        name = part.get(f'{{{PKG}}}name')
        ctype = part.get(f'{{{PKG}}}contentType')
        xml = part.find(f'{{{PKG}}}xmlData')
        binary = part.find(f'{{{PKG}}}binaryData')
        if xml is not None:
            data = etree.tostring(xml[0], xml_declaration=True, encoding='UTF-8', standalone=True)
        else:
            data = base64.b64decode(''.join(binary.text.split()))
        parts.append((name.lstrip('/'), data))
        if ctype != REL_TYPE:
            overrides.append((name, ctype))
    ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>']
    ct += [f'<Override PartName="{n}" ContentType="{c}"/>' for n, c in overrides]
    ct.append('</Types>')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '\n'.join(ct))
        for n, data in parts:
            z.writestr(n, data)
    return [n for n, _ in parts]


if __name__ == '__main__':
    names = convert(sys.argv[1], sys.argv[2])
    print(len(names), 'parts:', ', '.join(names[:40]))

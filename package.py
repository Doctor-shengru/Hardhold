#!/usr/bin/env python3
"""把 classes.dex 和 native 库塞进 aapt 打出的 base.apk，保持 resources.arsc 不压缩。"""
import sys, zipfile, os

src, dst = sys.argv[1], sys.argv[2]
extras = []
for spec in sys.argv[3:]:
    name, path = spec.split('=', 1)
    extras.append((name, path))

with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w') as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        zi.external_attr = info.external_attr
        # resources.arsc 必须 stor，其他资源保持原样
        zi.compress_type = zipfile.ZIP_STORED if info.filename == 'resources.arsc' else info.compress_type
        zout.writestr(zi, data)
    for name, path in extras:
        zi = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
        zi.compress_type = zipfile.ZIP_DEFLATED
        with open(path, 'rb') as f:
            zout.writestr(zi, f.read())
        print('  + %s (%.1f MB)' % (name, os.path.getsize(path) / 1048576))

### ziso - CSO to ISO converter

To create .exe or linux binary:

```
cd iso2ziso_converter
python3 -m pip install -r requirements.txt
python3 setup.py build
```

Usage:

```
ziso.exe -h
```
```
usage: ziso.py [-h] [-c COMPRESS_LEVEL] [-m] [-t COMPRESS_PERCENTAGE] [-ap ALIGN_PADDING] [-p PADDING_BYTE] [-a] [-f INPUT_FILE] [-d ISOS_DIR]

Script to compresso PS2 ISO to ZSO or ZSO to ISO.

optional arguments:
  -h, --help            show this help message and exit
  -c COMPRESS_LEVEL     Level: 1-9 compress ISO to ZSO, use any non-zero number it has no effect 0 decompress ZSO to ISO
  -m                    Use multiprocessing acceleration for compressing
  -t COMPRESS_PERCENTAGE
                        Percent Compression Threshold (1-100)
  -ap ALIGN_PADDING     Align Padding alignment 0=small/slow 6=fast/large
  -p PADDING_BYTE       Pad Padding byte
  -a, --all             All files in current dir
  -f INPUT_FILE, --file INPUT_FILE
                        Input ISO/ZSO file
  -d ISOS_DIR, --dir ISOS_DIR
                        A diretory with multiple ISO/ZSO files
```

The stock args is:

```
-c : 9
-m : True
-t : 100
-ap: 6
-p : br'X'
```

For `Rogue Galaxy` - `SCUS_974.90` this setting works fine, but the `-m` multiprocessing may not work for all games, so it doesn't finish the conversion.

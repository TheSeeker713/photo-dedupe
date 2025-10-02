modules = [
    'PySide6',
    'PIL',
    'pillow_heif',
    'imagehash',
    'cv2',
    'piexif',
    'xxhash',
    'blake3',
    'send2trash',
    'platformdirs',
    'loguru',
    'tqdm',
]

failed = []
for m in modules:
    try:
        __import__(m)
        print(f"Imported {m}")
    except Exception as e:
        print(f"FAILED {m}: {e}")
        failed.append((m, str(e)))

if failed:
    print('\nSome imports failed:')
    for m,err in failed:
        print(m, err)
    raise SystemExit(1)
else:
    print('\nAll imports succeeded')

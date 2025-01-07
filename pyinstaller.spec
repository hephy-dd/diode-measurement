import os
from pyinstaller_versionfile import create_versionfile

import diode_measurement

version = diode_measurement.__version__
filename = f"diode-measurement-{version}.exe"
console = False
block_cipher = None

package_root = os.path.join(os.path.dirname(diode_measurement.__file__))
package_icon = os.path.join(package_root, "assets", "icons", "diode-measurement.ico")

# Create entry point
def create_entrypoint(output_file):
    with open(output_file, "wt") as fp:
        fp.write("from diode_measurement.__main__ import main; main()")

create_entrypoint(output_file="entry_point.py")

# Create windows version info
create_versionfile(
    output_file="version_info.txt",
    version=f"{version}.0",
    company_name="HEPHY",
    file_description="IV/CV measurements for silicon sensors",
    internal_name="Diode Measurement",
    legal_copyright="Copyright 2021-2025 HEPHY. All rights reserved.",
    original_filename=filename,
    product_name="Diode Measurement"
)

a = Analysis(
    ["entry_point.py"],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        (os.path.join(package_root, "assets", "icons", "*.svg"), os.path.join("diode_measurement", "assets", "icons")),
        (os.path.join(package_root, "assets", "icons", "*.ico"), os.path.join("diode_measurement", "assets", "icons")),
    ],
    hiddenimports=[
        "pyvisa",
        "pyvisa_py",
        "pyserial",
        "pyusb"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=filename,
    version="version_info.txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    icon=package_icon
)

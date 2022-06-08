"""
    Setup.py to build .exe file with ex_freeze.
"""

import os
import sys
import shutil

from os import listdir
from os.path import join, exists, isfile

from cx_Freeze import setup, Executable

__version__ = "0.1"

BASE = "Console"
WORK_DIR = sys.path[0]

BASE_SCRIPT_NAME = [
    x for x in listdir(
        WORK_DIR
    ) if not "setup" in x and ".py" in x
][0]

BUILD_DIR = join(WORK_DIR, BASE_SCRIPT_NAME.replace(".py", ""))
FINAL_BUILD_ZIP = join(WORK_DIR, BASE_SCRIPT_NAME.replace(".py", ".zip"))

if sys.platform == "win32":
    WINDOWS_DLL_LIBS = [
        "C:\\Windows\\SysWOW64\\vcruntime140.dll"]
    for DLL_LIB in WINDOWS_DLL_LIBS:
        FILES_TO_INCLUDE.append(DLL_LIB)
    if BASE != "Console":
        BASE = "Win32GUI"

build_exe_options = {
    "build_exe": BUILD_DIR,
    "packages": ["os"],
    "excludes": [
        "tkinter",
        "PyQt5",
        # "pytz",
        # "numpy",
        # "email",
        # "idna",
        "lib2to3",
        "pkg_resources",
        "pydoc_data",
        "test",
        # "xml",
        # "xmlrpc",
        # "logging",
        "distutils",
    ],
    "include_msvcr": True,
}

setup(
    name=BASE_SCRIPT_NAME.replace(".py", ""),
    version=__version__,
    description=f"{BASE_SCRIPT_NAME} app",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            BASE_SCRIPT_NAME,
            base=BASE,
            icon=join(WORK_DIR, "icon.ico")
        )
    ],
)

print()
print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

for file in listdir(WORK_DIR):
    if ".zip" in file and not "compiled" in file:
        os.remove(join(WORK_DIR, file))
        print(".zip antigo deletado.")

if exists(BUILD_DIR):
    print("BUILD_DIR, encontrado!")
    if isfile(FINAL_BUILD_ZIP):
        os.remove(FINAL_BUILD_ZIP)
        print(".zip antigo deletado!")

    shutil.make_archive(
        "_v".join([FINAL_BUILD_ZIP, __version__]).replace(".zip", ""),
        "zip",
        BUILD_DIR
    )
    print("Arquivo .zip gerado com sucesso!")

print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

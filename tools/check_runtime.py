"""Comprobación silenciosa de la instalación para el lanzador de Windows."""
from importlib.metadata import version
import sys


def installed():
    if sys.version_info[:2] not in ((3, 11), (3, 12)):
        return False
    if version("Kivy") != "2.3.1" or version("kivymd") != "1.2.0":
        return False
    if not (1, 6) <= tuple(int(part) for part in version("segno").split(".")[:2]) < (2, 0):
        return False
    requests_version = tuple(int(part) for part in version("requests").split(".")[:2])
    return (2, 32) <= requests_version < (3, 0)


if __name__ == "__main__":
    sys.exit(0 if installed() else 1)

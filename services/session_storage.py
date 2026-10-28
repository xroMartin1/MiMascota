"""Encrypted session cache: Android Keystore and Windows user-bound DPAPI."""
import os
import sys
from pathlib import Path


class SessionStorage:
    def __init__(self, namespace='session', path=None):
        if namespace not in ('session', 'flow'):
            raise ValueError('Unknown cache')
        self.namespace = namespace
        self.path = Path(path) if path else Path(os.getenv('LOCALAPPDATA', '.')) / 'MiMascota' / (namespace + '.bin')

    def native(self):
        from kivy.utils import platform
        if platform != 'android':
            return None
        from jnius import autoclass
        return autoclass('org.mimascota.SessionVault'), autoclass('org.kivy.android.PythonActivity').mActivity

    @staticmethod
    def crypt(data, decrypt=False):
        import ctypes
        from ctypes import wintypes
        class Blob(ctypes.Structure):
            _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
        buffer = ctypes.create_string_buffer(data)
        source = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
        target = Blob()
        function = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
        if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
            raise OSError('Could not open encrypted cache')
        try:
            return ctypes.string_at(target.data, target.size)
        finally:
            ctypes.windll.kernel32.LocalFree(target.data)

    def read(self):
        if os.getenv('MIMASCOTA_DISABLE_SAVED_SESSION') == '1':
            return ''
        try:
            native = self.native()
            if native:
                method = native[0].readFlow if self.namespace == 'flow' else native[0].read
                return str(method(native[1]) or '')
            if sys.platform == 'win32' and self.path.exists():
                return self.crypt(self.path.read_bytes(), decrypt=True).decode('utf-8')
        except Exception:
            pass  # A temporary vault failure must not delete a valid cache.
        return ''

    def write(self, token):
        if os.getenv('MIMASCOTA_DISABLE_SAVED_SESSION') == '1':
            return True
        try:
            native = self.native()
            if native:
                method = native[0].saveFlow if self.namespace == 'flow' else native[0].save
                return bool(method(native[1], token))
            if sys.platform == 'win32':
                encrypted = self.crypt(token.encode('utf-8'))
                self.path.parent.mkdir(parents=True, exist_ok=True)
                temp = self.path.with_suffix('.tmp')
                with temp.open('wb') as stream:
                    stream.write(encrypted)
                    stream.flush()
                    os.fsync(stream.fileno())
                temp.replace(self.path)
                return True
        except Exception:
            pass
        return False

    def clear(self):
        if os.getenv('MIMASCOTA_DISABLE_SAVED_SESSION') == '1':
            return
        try:
            native = self.native()
            if native:
                method = native[0].clearFlow if self.namespace == 'flow' else native[0].clear
                method(native[1])
            elif sys.platform == 'win32':
                self.path.unlink(missing_ok=True)
        except Exception:
            pass

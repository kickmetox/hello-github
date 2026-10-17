"""Registrierungszugriff. Auf anderen Systemen als Windows bleibt es eine Speicherfassung."""

from __future__ import annotations

from typing import Any


def _norm(path: str) -> str:
    return path.replace("/", "\\").rstrip("\\").lower()


class MemoryRegistry:
    """Abbild der Registry für Tests und den Vorschau-Modus."""

    def __init__(self, admin: bool = False) -> None:
        self.admin = admin
        self.values: dict[tuple[str, str, str], tuple[str, Any]] = {}

    def set_admin(self, admin: bool) -> None:
        self.admin = admin

    def _check(self, hive: str) -> None:
        if hive.upper() == "HKLM" and not self.admin:
            raise PermissionError("Administratorrechte erforderlich")

    def _key(self, hive: str, path: str, name: str) -> tuple[str, str, str]:
        return (hive.upper(), _norm(path), name.lower())

    def set_sz(self, hive: str, path: str, name: str, value: str) -> None:
        self._check(hive)
        self.values[self._key(hive, path, name)] = ("sz", str(value))

    def set_dword(self, hive: str, path: str, name: str, value: int) -> None:
        self._check(hive)
        self.values[self._key(hive, path, name)] = ("dword", int(value))

    def get_sz(self, hive: str, path: str, name: str) -> str | None:
        item = self.values.get(self._key(hive, path, name))
        if item and item[0] == "sz":
            return str(item[1])
        return None

    def get_dword(self, hive: str, path: str, name: str) -> int | None:
        item = self.values.get(self._key(hive, path, name))
        if item and item[0] == "dword":
            return int(item[1])
        return None

    def delete_value(self, hive: str, path: str, name: str) -> None:
        self._check(hive)
        self.values.pop(self._key(hive, path, name), None)

    def delete_tree(self, hive: str, path: str) -> None:
        self._check(hive)
        hive_name = hive.upper()
        prefix = _norm(path)
        doomed = [
            key
            for key in self.values
            if key[0] == hive_name and (key[1] == prefix or key[1].startswith(prefix + "\\"))
        ]
        for key in doomed:
            del self.values[key]

    def subkeys(self, hive: str, path: str) -> list[str]:
        hive_name = hive.upper()
        prefix = _norm(path)
        children: set[str] = set()
        for key_hive, key_path, _name in self.values:
            if key_hive != hive_name:
                continue
            if key_path == prefix:
                continue
            if key_path.startswith(prefix + "\\"):
                rest = key_path[len(prefix) + 1:]
                children.add(rest.split("\\", 1)[0])
        return sorted(children)


class WindowsRegistry:
    def set_sz(self, hive: str, path: str, name: str, value: str) -> None:
        self._set(hive, path, name, "sz", value)

    def set_dword(self, hive: str, path: str, name: str, value: int) -> None:
        self._set(hive, path, name, "dword", int(value))

    def get_sz(self, hive: str, path: str, name: str) -> str | None:
        return self._get(hive, path, name, "sz")

    def get_dword(self, hive: str, path: str, name: str) -> int | None:
        value = self._get(hive, path, name, "dword")
        return None if value is None else int(value)

    def delete_value(self, hive: str, path: str, name: str) -> None:
        import winreg

        try:
            with winreg.OpenKey(self._root(hive), path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
        except FileNotFoundError:
            return
        except OSError as exc:
            self._raise(exc)

    def delete_tree(self, hive: str, path: str) -> None:
        for child in self.subkeys(hive, path):
            self.delete_tree(hive, path + "\\" + child)
        import winreg

        try:
            winreg.DeleteKey(self._root(hive), path)
        except FileNotFoundError:
            return
        except OSError as exc:
            self._raise(exc)

    def subkeys(self, hive: str, path: str) -> list[str]:
        import winreg

        try:
            key = winreg.OpenKey(self._root(hive), path)
        except FileNotFoundError:
            return []
        except OSError as exc:
            self._raise(exc)
            return []
        names: list[str] = []
        try:
            index = 0
            while True:
                try:
                    names.append(winreg.EnumKey(key, index))
                except OSError:
                    break
                index += 1
        finally:
            key.Close()
        return names

    def _set(self, hive: str, path: str, name: str, kind: str, value: Any) -> None:
        import winreg

        reg_kind = winreg.REG_SZ if kind == "sz" else winreg.REG_DWORD
        try:
            key = winreg.CreateKey(self._root(hive), path)
            try:
                winreg.SetValueEx(key, name, 0, reg_kind, value)
            finally:
                key.Close()
        except OSError as exc:
            self._raise(exc)

    def _get(self, hive: str, path: str, name: str, kind: str) -> Any:
        import winreg

        expected = winreg.REG_SZ if kind == "sz" else winreg.REG_DWORD
        try:
            with winreg.OpenKey(self._root(hive), path) as key:
                value, stored = winreg.QueryValueEx(key, name)
        except FileNotFoundError:
            return None
        except OSError as exc:
            if getattr(exc, "winerror", None) == 2:
                return None
            self._raise(exc)
            return None
        if stored != expected:
            return None
        return value

    def _root(self, hive: str) -> Any:
        import winreg

        if hive.upper() == "HKCU":
            return winreg.HKEY_CURRENT_USER
        if hive.upper() == "HKLM":
            return winreg.HKEY_LOCAL_MACHINE
        raise ValueError(f"Unbekannter Hive: {hive}")

    def _raise(self, exc: OSError) -> None:
        if isinstance(exc, FileNotFoundError):
            raise exc
        if getattr(exc, "winerror", None) == 5:
            raise PermissionError("Administratorrechte erforderlich") from exc
        raise exc

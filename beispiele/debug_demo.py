"""Haltepunkt auf die Zeile mit `wert =` setzen und die Variable ansehen."""


def faktoren(zahl: int) -> list[int]:
    werte = []
    for teiler in range(1, zahl + 1):
        if zahl % teiler == 0:
            werte.append(teiler)
    return werte


def main() -> None:
    wert = faktoren(12)
    print(wert)


if __name__ == "__main__":
    main()

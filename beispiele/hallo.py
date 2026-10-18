"""Beispiel für ShatuIDE."""


def begruessung(name: str) -> str:
    return f"Hallo {name}"


def summe(a: int, b: int) -> int:
    return a + b


def main() -> None:
    # TODO: Begrüßung konfigurierbar machen
    print(begruessung("Andreas"))
    total = 0
    for number in range(5):
        total = summe(total, number)
    print("Summe:", total)


if __name__ == "__main__":
    main()

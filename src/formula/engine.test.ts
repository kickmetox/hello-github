import { describe, expect, it } from 'vitest';
import { adjustFormulaCopy, adjustFormulaStructure } from './adjust';
import { calculate, resultAt, type CalcInput, type Computed } from './engine';
import { translateFormula } from './translate';

function book(cells: Record<string, string>, extra?: Partial<CalcInput>): CalcInput {
  const mapped: CalcInput['sheets'][0]['cells'] = {};
  let rows = 8;
  let cols = 6;
  for (const [addr, raw] of Object.entries(cells)) {
    const m = /^([A-Z]+)(\d+)$/.exec(addr.toUpperCase());
    if (!m) throw new Error(addr);
    let n = 0;
    for (const ch of m[1]) n = n * 26 + (ch.charCodeAt(0) - 64);
    const r = Number(m[2]) - 1;
    const c = n - 1;
    mapped[`${r},${c}`] = { raw };
    rows = Math.max(rows, r + 3);
    cols = Math.max(cols, c + 3);
  }
  return {
    sheets: [{ name: 'Tabelle1', rows, cols, cells: mapped }],
    ...extra,
  };
}

function val(map: Map<string, Computed>, addr: string): Computed | undefined {
  return resultAt(map, 'Tabelle1', addr);
}

describe('Rechnen', () => {
  it('beachtet Punkt vor Strich und Klammern', () => {
    const map = calculate(book({ A1: '=1+2*3', A2: '=(1+2)*3', A3: '=-3^2', A4: '=2+50%', A5: '=1,5+2' }));
    expect(val(map, 'A1')?.value).toBe(7);
    expect(val(map, 'A2')?.value).toBe(9);
    expect(val(map, 'A3')?.value).toBe(9);
    expect(val(map, 'A4')?.value).toBe(2.5);
    expect(val(map, 'A5')?.value).toBe(3.5);
  });

  it('summiert Bereiche und ignoriert Text', () => {
    const map = calculate(book({ A1: '1', A2: '2', A3: 'x', A4: '=SUMME(A1:A3)', A5: '=MITTELWERT(A1:A2)', A6: '=ANZAHL(A1:A3)', A7: '=ANZAHL2(A1:A3)' }));
    expect(val(map, 'A4')?.value).toBe(3);
    expect(val(map, 'A5')?.value).toBe(1.5);
    expect(val(map, 'A6')?.value).toBe(2);
    expect(val(map, 'A7')?.value).toBe(3);
  });

  it('rechnet WENN, UND und Verkettung', () => {
    const map = calculate(book({ A1: '10', B1: '=WENN(A1>5;"hoch";"niedrig")', B2: '=UND(A1>0;A1<20)', B3: '="Umsatz: "&A1' }));
    expect(val(map, 'B1')?.value).toBe('hoch');
    expect(val(map, 'B2')?.value).toBe(true);
    expect(val(map, 'B3')?.value).toBe('Umsatz: 10');
  });

  it('fängt Division durch Null ab', () => {
    const map = calculate(book({ A1: '=1/0', A2: '=WENNFEHLER(1/0;"–")' }));
    expect(val(map, 'A1')?.error).toBe('#DIV/0!');
    expect(val(map, 'A2')?.value).toBe('–');
  });

  it('erkennt Zirkelbezüge', () => {
    const map = calculate(book({ A1: '=A1+1' }));
    expect(val(map, 'A1')?.error).toBe('#BEZUG!');
  });
});

describe('Suche und dynamische Arrays', () => {
  it('findet mit SVERWEIS und XVERWEIS', () => {
    const map = calculate(
      book({
        A1: 'Nord',
        B1: '10',
        A2: 'Süd',
        B2: '20',
        C1: '=SVERWEIS("Süd";A1:B2;2;FALSCH)',
        C2: '=XVERWEIS("Nord";A1:A2;B1:B2)',
        C3: '=INDEX(B1:B2;VERGLEICH("Süd";A1:A2;0))',
      }),
    );
    expect(val(map, 'C1')?.value).toBe(20);
    expect(val(map, 'C2')?.value).toBe(10);
    expect(val(map, 'C3')?.value).toBe(20);
  });

  it('verschüttet FILTER, SORTIEREN, EINDEUTIG und SEQUENZ', () => {
    const map = calculate(
      book({
        A1: 'Nord',
        B1: '3',
        A2: 'Süd',
        B2: '1',
        A3: 'Nord',
        B3: '8',
        D1: '=FILTER(A1:B3;A1:A3="Nord")',
        F1: '=EINDEUTIG(A1:A3)',
        H1: '=SEQUENZ(3;1;10;5)',
        J1: '=SORTIEREN(A1:B3;2;-1)',
      }),
    );
    expect(val(map, 'D1')?.value).toBe('Nord');
    expect(val(map, 'E1')?.value).toBe(3);
    expect(val(map, 'D2')?.value).toBe('Nord');
    expect(val(map, 'E2')?.value).toBe(8);
    expect(val(map, 'F1')?.value).toBe('Nord');
    expect(val(map, 'F2')?.value).toBe('Süd');
    expect(val(map, 'H1')?.value).toBe(10);
    expect(val(map, 'H2')?.value).toBe(15);
    expect(val(map, 'H3')?.value).toBe(20);
    expect(val(map, 'K1')?.value).toBe(8);
  });

  it('wendet LAMBDA und LET an', () => {
    const map = calculate(
      book({
        A1: '=LAMBDA(x;x*2)(21)',
        A2: '=LET(preis;10;menge;3;preis*menge)',
        A3: '=MAP(B1:B2;LAMBDA(x;x+1))',
        B1: '4',
        B2: '5',
      }),
    );
    expect(val(map, 'A1')?.value).toBe(42);
    expect(val(map, 'A2')?.value).toBe(30);
    expect(val(map, 'A3')?.value).toBe(5);
    expect(val(map, 'A4')?.value).toBe(6);
  });
});

describe('Datenbankfunktionen', () => {
  const db = {
    A1: 'Region',
    B1: 'Jahr',
    C1: 'Umsatz',
    A2: 'Nord',
    B2: '2025',
    C2: '12000',
    A3: 'Nord',
    B3: '2026',
    C3: '18500',
    A4: 'Süd',
    B4: '2026',
    C4: '9600',
    A5: 'Nord',
    B5: '2026',
    C5: '7300',
    E1: 'Region',
    F1: 'Jahr',
    E2: 'Nord',
    F2: '>2025',
    H1: '=DSUMME(A1:C5;"Umsatz";E1:F2)',
    H2: '=DANZAHL(A1:C5;"Umsatz";E1:F2)',
    H3: '=DMAX(A1:C5;"Umsatz";E1:F2)',
    H4: '=DMIN(A1:C5;"Umsatz";E1:F2)',
    H5: '=DMITTELWERT(A1:C5;"Umsatz";E1:F2)',
    E4: 'Region',
    F4: 'Jahr',
    E5: 'Süd',
    F5: '2026',
    H6: '=DAUSZUG(A1:C5;"Umsatz";E4:F5)',
    H7: '=SUMMEWENN(A2:A5;"Nord";C2:C5)',
    H8: '=ABFRAGE("SELECT Region, SUM(Umsatz) AS Summe FROM A1:C5 WHERE Jahr > 2025 GROUP BY Region ORDER BY Summe DESC")',
  };

  it('wertet DSUMME, DMAX, DAUSZUG und die Abfrage aus', () => {
    const map = calculate(book(db));
    expect(val(map, 'H1')?.value).toBe(25800);
    expect(val(map, 'H2')?.value).toBe(2);
    expect(val(map, 'H3')?.value).toBe(18500);
    expect(val(map, 'H4')?.value).toBe(7300);
    expect(val(map, 'H5')?.value).toBe(12900);
    expect(val(map, 'H6')?.value).toBe(9600);
    expect(val(map, 'H7')?.value).toBe(12000 + 18500 + 7300);
    expect(val(map, 'H8')?.value).toBe('Region');
    expect(val(map, 'I8')?.value).toBe('Summe');
    expect(val(map, 'H9')?.value).toBe('Nord');
    expect(val(map, 'I9')?.value).toBe(25800);
  });
});

describe('Datum, Finanzen, Technik', () => {
  it('rechnet Datumsteile und Arbeitstage', () => {
    const map = calculate(
      book({
        A1: '=DATUM(2026;10;20)',
        A2: '=JAHR(A1)',
        A3: '=MONAT(A1)',
        A4: '=TAG(A1)',
        A5: '=TAGE(DATUM(2026;10;20);DATUM(2026;10;10))',
        A6: '=NETTOARBEITSTAGE(DATUM(2026;10;19);DATUM(2026;10;23))',
        A7: '=DATEDIF(DATUM(2020;1;15);DATUM(2026;10;20);"Y")',
      }),
    );
    expect(val(map, 'A2')?.value).toBe(2026);
    expect(val(map, 'A3')?.value).toBe(10);
    expect(val(map, 'A4')?.value).toBe(20);
    expect(val(map, 'A5')?.value).toBe(10);
    expect(val(map, 'A6')?.value).toBe(5);
    expect(val(map, 'A7')?.value).toBe(6);
  });

  it('rechnet RMZ und IKV', () => {
    const map = calculate(book({ A1: '=RMZ(0,05/12;36;10000)', A2: '=RUNDEN(A1;2)', B1: '=IKV({-1000;300;400;500})' }));
    expect(val(map, 'A2')?.value).toBeCloseTo(-299.71, 2);
    expect(typeof val(map, 'B1')?.value).toBe('number');
    expect(val(map, 'B1')?.value as number).toBeGreaterThan(0);
  });

  it('rechnet um und konvertiert Zahlensysteme', () => {
    const map = calculate(
      book({
        A1: '=RUNDEN(UMWANDELN(100;"C";"F");2)',
        A2: '=BININDEZ("1010")',
        A3: '=DEZINHEX(255)',
        D1: '=MMULT({1\\2;3\\4};{1\\0;0\\1})',
        D4: '=MDET({1\\2;3\\4})',
      }),
    );
    expect(val(map, 'A1')?.value).toBe(212);
    expect(val(map, 'A2')?.value).toBe(10);
    expect(val(map, 'A3')?.value).toBe('FF');
    expect(val(map, 'D1')?.value).toBe(1);
    expect(val(map, 'E1')?.value).toBe(2);
    expect(val(map, 'D2')?.value).toBe(3);
    expect(val(map, 'E2')?.value).toBe(4);
    expect(val(map, 'D4')?.value).toBeCloseTo(-2, 6);
  });
});

describe('Bezüge und Übersetzung', () => {
  it('verschiebt relative Bezüge beim Kopieren', () => {
    expect(adjustFormulaCopy('=SUMME(A1:A2)*$B$1', 1, 1)).toBe('=SUMME(B2:B3)*$B$1');
    expect(adjustFormulaCopy('=(A1+B1)*2', 0, 1)).toBe('=(B1+C1)*2');
  });

  it('passt Bezüge beim Einfügen von Zeilen an', () => {
    expect(adjustFormulaStructure('=SUMME(A1:A10)', 'Tabelle1', 'Tabelle1', 'row', 2, 1)).toBe('=SUMME(A1:A11)');
    expect(adjustFormulaStructure('=A5', 'Tabelle1', 'Tabelle1', 'row', 4, -1)).toBe('=#BEZUG!');
  });

  it('übersetzt Funktionsnamen und Trennzeichen', () => {
    expect(translateFormula('=SUMME(A1;RUNDEN(1,5;2))', 'de-en')).toBe('=SUM(A1,ROUND(1.5,2))');
    expect(translateFormula('=SUM(A1,ROUND(1.5,2))', 'en-de')).toBe('=SUMME(A1;RUNDEN(1,5;2))');
    expect(translateFormula('=SUMME(A1;"SUMME")', 'de-en')).toBe('=SUM(A1,"SUMME")');
  });
});

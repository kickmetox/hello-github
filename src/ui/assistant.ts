import { FUNCTION_LIST, registry } from '../formula/functions';
import { translateFormula } from '../formula/translate';

export function generateFormula(prompt: string, rangeHint = 'A1:A10'): string {
  const range = /([A-Za-z]{1,3}\d+\s*:\s*[A-Za-z]{1,3}\d+)/.exec(prompt)?.[1]?.replace(/\s/g, '') ?? rangeHint;
  const low = prompt.toLocaleLowerCase('de-DE');
  if (/dsumme|datenbank/.test(low)) return `=DSUMME(${range};D4;G5:H6)`;
  if (/xverweis/.test(low)) return `=XVERWEIS(A2;${range};B:B;"")`;
  if (/sverweis/.test(low)) return `=SVERWEIS(A2;${range};2;FALSCH)`;
  if (/eindeutig/.test(low)) return `=EINDEUTIG(${range})`;
  if (/sortier/.test(low)) return `=SORTIEREN(${range})`;
  if (/^filter|gefiltert|extrahier/.test(low) || low.includes('filter(')) return `=FILTER(${range};A:A<>"")`;
  if (/mittel|durchschnitt/.test(low)) return `=MITTELWERT(${range})`;
  if (/zählenwenn|zaehlenwenn|countif/.test(low)) return `=ZÄHLENWENN(${range};"")`;
  if (/summewenn/.test(low)) return `=SUMMEWENN(${range};"";${range})`;
  if (/anzahl2/.test(low)) return `=ANZAHL2(${range})`;
  if (/anzahl/.test(low)) return `=ANZAHL(${range})`;
  if (/maximum|\bmax\b/.test(low)) return `=MAX(${range})`;
  if (/minimum|\bmin\b/.test(low)) return `=MIN(${range})`;
  if (/wennfehler/.test(low)) return `=WENNFEHLER(${range};0)`;
  if (/wenn/.test(low)) return `=WENN(A1>0;"ja";"nein")`;
  if (/lambda/.test(low)) return '=LAMBDA(x;x*2)(A1)';
  if (/heute/.test(low)) return '=HEUTE()';
  if (/jetzt/.test(low)) return '=JETZT()';
  if (/rund/.test(low)) return '=RUNDEN(A1;2)';
  if (/verkett|textkette|zusammen/.test(low)) return '=TEXTKETTE(A1;B1)';
  if (/rate|rmz|kredit|annuit/.test(low)) return '=RMZ(B4/12;B5*12;B3)';
  if (/spark|miniatur|trend/.test(low)) return `=MINIATUR(${range};"linie")`;
  if (/summe|addier|gesamt/.test(low)) return `=SUMME(${range})`;
  return `=SUMME(${range})`;
}

export function explainFormula(formula: string): string {
  const body = formula.trim().replace(/^=/, '');
  if (!body) return 'Die Zelle enthält keine Formel.';
  const names = new Set<string>();
  for (const match of body.matchAll(/[A-ZÄÖÜa-zäöü][A-ZÄÖÜa-zäöü0-9.]*/g)) {
    const token = match[0].toUpperCase();
    if (registry.has(token)) names.add(token);
  }
  if (!names.size) {
    return 'Die Formel enthält Operatoren oder Bezüge, aber keine benannte Funktion. Punkt-vor-Strich und Klammern gelten.';
  }
  const lines = [`Formel: =${body}`];
  for (const name of names) {
    const info = FUNCTION_LIST.find((fn) => fn.de.toUpperCase() === name || fn.en.toUpperCase() === name);
    if (info) lines.push(`${info.de}: ${info.desc} Syntax: ${info.signature}`);
  }
  return lines.join('\n');
}

export function repairFormula(formula: string, error: string | null): { formula: string; note: string } {
  let next = formula.trim();
  if (!next.startsWith('=')) next = `=${next}`;
  const notes: string[] = [];
  if (/\b(SUM|AVERAGE|VLOOKUP|HLOOKUP|XLOOKUP|IF|IFS|COUNT|COUNTA|ROUND|TODAY|NOW|AND|OR|NOT|FILTER|UNIQUE|SORT|SUMIF|INDEX|MATCH|PMT|TEXT)\s*\(/i.test(next)) {
    next = translateFormula(next, 'en-de');
    notes.push('Englische Funktionsnamen wurden ins Deutsche übersetzt.');
  }
  const open = [...next].filter((ch) => ch === '(').length;
  const close = [...next].filter((ch) => ch === ')').length;
  if (open > close) {
    next += ')'.repeat(open - close);
    notes.push('Fehlende schließende Klammern ergänzt.');
  }
  const unknown = [...next.matchAll(/([A-ZÄÖÜa-zäöü]{2,})\s*\(/g)]
    .map((m) => m[1].toUpperCase())
    .filter((name) => !registry.has(name) && !['WAHR', 'FALSCH'].includes(name));
  for (const name of unknown) {
    const guess = closest(name, [...registry.keys()]);
    if (guess) notes.push(`${name} ist unbekannt. Ähnlich: ${guess}.`);
  }
  if (error) notes.push(`Letzter Fehler: ${error}.`);
  if (!notes.length) notes.push('Die Formel ist syntaktisch ausgeglichen. Prüfe Bezüge und Argumenttrenner (Strichpunkt).');
  return { formula: next, note: notes.join(' ') };
}

function closest(name: string, pool: string[]): string | null {
  let best: string | null = null;
  let score = 3;
  for (const item of pool) {
    const d = distance(name, item);
    if (d < score) {
      score = d;
      best = item;
    }
  }
  return best;
}

function distance(a: string, b: string): number {
  if (Math.abs(a.length - b.length) > 3) return 9;
  const dp: number[] = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = dp[0];
    dp[0] = i;
    for (let j = 1; j <= b.length; j++) {
      const cur = dp[j];
      dp[j] = a[i - 1] === b[j - 1] ? prev : 1 + Math.min(prev, dp[j], dp[j - 1]);
      prev = cur;
    }
  }
  return dp[b.length];
}

import { deToEn, enToDe } from './functions';

/** Übersetzt Formeln zwischen deutschen und englischen Funktionsnamen und Trennzeichen. */
export function translateFormula(formula: string, direction: 'de-en' | 'en-de'): string {
  const map = direction === 'de-en' ? deToEn : enToDe;
  let out = '';
  let i = 0;
  while (i < formula.length) {
    const c = formula[i];
    if (c === '"') {
      let j = i + 1;
      let s = '"';
      while (j < formula.length) {
        s += formula[j];
        if (formula[j] === '"') {
          if (formula[j + 1] === '"') {
            s += '"';
            j += 2;
            continue;
          }
          j++;
          break;
        }
        j++;
      }
      out += s;
      i = j;
      continue;
    }
    if (/[A-Za-zÄÖÜäöü_]/.test(c)) {
      let j = i + 1;
      while (j < formula.length && /[A-Za-zÄÖÜäöü0-9_.]/.test(formula[j])) j++;
      const ident = formula.slice(i, j);
      const repl = map.get(ident.toUpperCase());
      out += repl ?? ident;
      i = j;
      continue;
    }
    if (/\d/.test(c)) {
      let j = i;
      while (j < formula.length && /\d/.test(formula[j])) j++;
      if (direction === 'en-de') {
        if (formula[j] === '.' && /\d/.test(formula[j + 1] ?? '')) {
          j++;
          while (j < formula.length && /\d/.test(formula[j])) j++;
        }
        out += formula.slice(i, j).replace('.', ',');
        i = j;
        continue;
      }
      if (formula[j] === ',' && /\d/.test(formula[j + 1] ?? '')) {
        j++;
        while (j < formula.length && /\d/.test(formula[j])) j++;
      } else if (formula[j] === '.' && /\d/.test(formula[j + 1] ?? '')) {
        const start = j;
        while (formula[j] === '.' && /\d{3}/.test(formula.slice(j + 1, j + 4))) j += 4;
        if (formula[j] === ',' && /\d/.test(formula[j + 1] ?? '')) {
          j++;
          while (j < formula.length && /\d/.test(formula[j])) j++;
        } else if (j === start) {
          j++;
          while (j < formula.length && /\d/.test(formula[j])) j++;
        }
      }
      let num = formula.slice(i, j);
      if (/^\d{1,3}(\.\d{3})+(,\d+)?$/.test(num)) num = num.replace(/\./g, '').replace(',', '.');
      else if (num.includes(',') && !num.includes('.')) num = num.replace(',', '.');
      out += num;
      i = j;
      continue;
    }
    if (c === ';' && direction === 'de-en') out += ',';
    else if (c === ',' && direction === 'en-de') out += ';';
    else out += c;
    i++;
  }
  return out;
}

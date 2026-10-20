import { describe, expect, it } from 'vitest';
import { GridController } from './controller';
import { blankTemplate, umsatzTemplate } from './templates';

describe('Arbeitsmappe', () => {
  it('rechnet die D-Funktionen der Umsatzvorlage', () => {
    const grid = new GridController(umsatzTemplate());
    expect(grid.numAt(8, 7)).toBe(31200);
    expect(grid.numAt(9, 7)).toBe(3);
    expect(grid.display(8, 7)).toContain('31.200');
  });

  it('aktualisiert DSUMME nach einer Zelländerung', () => {
    const grid = new GridController(umsatzTemplate());
    expect(grid.setCell(5, 3, '1000')).toBe(true);
    expect(grid.numAt(8, 7)).toBe(13700);
    grid.undo();
    expect(grid.numAt(8, 7)).toBe(31200);
  });

  it('führt ein Python-Skript auf dem Blatt aus', () => {
    const grid = new GridController(blankTemplate());
    const out = grid.runScript('py', 's = 0\nfor i in range(1, 4):\n    s = s + i\nprint(s)\nset("A1", s)\n');
    expect(out).toContain('6');
    expect(grid.sheet().cells['0,0']?.raw).toBe('6');
  });

  it('versteht ein kurzes VBA-Fragment', () => {
    const grid = new GridController(blankTemplate());
    grid.runScript('vba', 'Range("B2").Value = 7\nCells(3, 2).Value = Range("B2").Value * 6\nMsgBox "fertig"');
    expect(grid.sheet().cells['1,1']?.raw).toBe('7');
    expect(grid.numAt(2, 1)).toBe(42);
  });
});

import { useSyncExternalStore } from 'react';
import type { GridController } from '../model/controller';

export function useGrid(ctl: GridController): number {
  return useSyncExternalStore(ctl.subscribe, ctl.getSnapshot, ctl.getSnapshot);
}

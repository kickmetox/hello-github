import type { Expr } from './parser';

export type Scalar = number | string | boolean | null;

export class FError {
  constructor(public code: string) {}
  toString(): string {
    return this.code;
  }
}

export function isErr(v: unknown): v is FError {
  return v instanceof FError;
}

export const DIV0 = (): FError => new FError('#DIV/0!');
export const WERT = (): FError => new FError('#WERT!');
export const BEZUG = (): FError => new FError('#BEZUG!');
export const NAME = (): FError => new FError('#NAME?');
export const NV = (): FError => new FError('#NV');
export const ZAHL = (): FError => new FError('#ZAHL!');
export const UEBER = (): FError => new FError('#ÜBERLAUF!');
export const BERECH = (): FError => new FError('#BERECH!');
export const FEHLER = (): FError => new FError('#FEHLER!');

export type CellVal = Scalar | FError;

export interface Matrix {
  type: 'matrix';
  values: CellVal[][];
  sheet?: string;
  r1?: number;
  c1?: number;
}

export function isMatrix(v: unknown): v is Matrix {
  return !!v && typeof v === 'object' && (v as Matrix).type === 'matrix';
}

export class SparkVal {
  constructor(
    public values: number[],
    public mode: 'line' | 'col' | 'winloss',
  ) {}
}

export class LinkVal {
  constructor(
    public href: string,
    public label: string,
  ) {}
}

export class LambdaVal {
  constructor(
    public params: string[],
    public body: Expr,
    public sheet: string,
  ) {}
}

export function isSpark(v: unknown): v is SparkVal {
  return v instanceof SparkVal;
}
export function isLink(v: unknown): v is LinkVal {
  return v instanceof LinkVal;
}
export function isLambda(v: unknown): v is LambdaVal {
  return v instanceof LambdaVal;
}

export type Value = Scalar | FError | Matrix | SparkVal | LinkVal | LambdaVal;

export function matrix(values: CellVal[][], origin?: { sheet?: string; r1?: number; c1?: number }): Matrix {
  return { type: 'matrix', values, ...origin };
}

"""Kleiner Taschenrechner für die Trefferliste. Nur Arithmetik, kein eval."""

from __future__ import annotations

import ast
import operator
import re

_ALLOWED = re.compile(r"[0-9\.\+\-\*\/\(\)\s%]+")
_BIN = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval(node: ast.AST, depth: int = 0) -> float:
    if depth > 32:
        raise ValueError("too deep")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
        left = _eval(node.left, depth + 1)
        right = _eval(node.right, depth + 1)
        if isinstance(node.op, ast.Pow) and (abs(left) > 1_000_000 or abs(right) > 64):
            raise ValueError("pow")
        return float(_BIN[type(node.op)](left, right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return float(_UNARY[type(node.op)](_eval(node.operand, depth + 1)))
    raise ValueError("expr")


def try_calc(expr: str) -> str | None:
    raw = expr.strip()
    if not raw or len(raw) > 80:
        return None
    cooked = raw.replace("^", "**").replace(",", ".")
    if "**" not in cooked and not any(op in cooked for op in "+-*/%"):
        return None
    probe = cooked.replace("**", "")
    if not _ALLOWED.fullmatch(probe):
        return None
    try:
        tree = ast.parse(cooked, mode="eval")
        value = _eval(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError, ArithmeticError):
        return None
    if value != value or abs(value) == float("inf"):  # NaN / inf
        return None
    if abs(value - round(value)) < 1e-9 and abs(value) < 1e15:
        return str(int(round(value)))
    text = f"{value:.10g}"
    return text

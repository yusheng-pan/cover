#!/usr/bin/env python3
"""
Test suite for the core conversion functions in cover.py
Does not require tkinter.
"""

import re
from typing import Tuple, Optional

# Core functions extracted for testing
CHINESE_CHAR_RANGE = r'[\u4e00-\u9fa5]'
OPERATORS_NEEDING_PARENS = {'+', '-', '*', '/'}


def add_spacing_around_dollars(text: str) -> str:
    """Add a space between adjacent Chinese characters and $ symbols."""
    text = re.sub(rf'({CHINESE_CHAR_RANGE})\$', r'\1 $', text)
    text = re.sub(rf'\$({CHINESE_CHAR_RANGE})', r'$ \1', text)
    return text


def find_matching_brace(text: str, start_pos: int) -> int:
    """Find the position of the closing brace that matches the opening brace."""
    if start_pos >= len(text) or text[start_pos] != '{':
        raise ValueError("start_pos must point to an opening brace")
    
    depth = 0
    for i in range(start_pos, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1


def extract_frac_arguments(text: str) -> Optional[Tuple[str, str, int]]:
    """Extract numerator and denominator from \\frac{...}{...} pattern."""
    frac_match = re.search(r'\\frac\s*\{', text)
    if not frac_match:
        return None
    
    brace_start = frac_match.end() - 1
    try:
        numerator_end = find_matching_brace(text, brace_start)
    except ValueError:
        return None
        
    if numerator_end == -1:
        return None
    
    numerator = text[brace_start + 1:numerator_end]
    
    denominator_start_match = re.match(r'\s*\{', text[numerator_end + 1:])
    if not denominator_start_match:
        return None
    
    denominator_start = numerator_end + 1 + denominator_start_match.start()
    try:
        denominator_brace_pos = find_matching_brace(text, denominator_start)
    except ValueError:
        return None
        
    if denominator_brace_pos == -1:
        return None
    
    denominator = text[denominator_start + 1:denominator_brace_pos]
    
    return numerator, denominator, denominator_brace_pos


def needs_parentheses(expression: str) -> bool:
    """Determine if an expression needs to be wrapped in parentheses."""
    expr = expression.strip()
    if not expr:
        return False

    if expr[0] == '(' and expr[-1] == ')':
        balance = 0
        for i, char in enumerate(expr):
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
                if balance == 0 and i == len(expr) - 1:
                    return False

    if any(op in expr for op in OPERATORS_NEEDING_PARENS) or ' ' in expr:
        return True

    return False


def latex_frac_to_typst_slash(text: str) -> str:
    """Recursively convert LaTeX \\frac{numerator}{denominator} to Typst slash format."""
    if '\\frac' not in text:
        return text
    
    result = []
    pos = 0
    
    while pos < len(text):
        frac_data = extract_frac_arguments(text[pos:])
        
        if frac_data is None:
            result.append(text[pos:])
            break
        
        numerator, denominator, end_pos = frac_data
        frac_start = text[pos:].find('\\frac')
        
        result.append(text[pos:pos + frac_start])
        
        numerator = latex_frac_to_typst_slash(numerator)
        denominator = latex_frac_to_typst_slash(denominator)
        
        numerator_str = f"({numerator})" if needs_parentheses(numerator) else numerator
        denominator_str = f"({denominator})" if needs_parentheses(denominator) else denominator
        
        result.append(f"{numerator_str}/{denominator_str}")
        pos += end_pos + 1
    
    return ''.join(result)


def run_tests():
    """Run all tests."""
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("TEST 1: add_spacing_around_dollars")
    print("=" * 70)
    test_cases = [
        ("中文$x$文本", "中文 $x$ 文本"),
        ("公式$a$和$b$", "公式 $a$ 和 $b$"),
        ("$中$", "$ 中 $"),
        ("a$b$c", "a$b$c"),  # English letters should not be affected
    ]
    for input_text, expected in test_cases:
        result = add_spacing_around_dollars(input_text)
        if result == expected:
            print(f"✅ PASS: {input_text!r}")
            passed += 1
        else:
            print(f"❌ FAIL: {input_text!r}")
            print(f"   Expected: {expected!r}")
            print(f"   Got:      {result!r}")
            failed += 1

    print()
    print("=" * 70)
    print("TEST 2: needs_parentheses")
    print("=" * 70)
    test_cases = [
        ("a", False),
        ("a+b", True),
        ("(a+b)", False),
        ("a b", True),
        ("(a)(b)", False),  # Already wrapped, no extra parens needed
        ("", False),
        ("123", False),
        ("x*y", True),
    ]
    for expr, expected in test_cases:
        result = needs_parentheses(expr)
        if result == expected:
            print(f"✅ PASS: {expr!r:20} => {result}")
            passed += 1
        else:
            print(f"❌ FAIL: {expr!r:20} => {result} (expected {expected})")
            failed += 1

    print()
    print("=" * 70)
    print("TEST 3: find_matching_brace")
    print("=" * 70)
    test_cases = [
        (r"\frac{a+b}{c}", 5, 9),  # (text, start_pos, expected_end_pos)
        ("{hello}", 0, 6),
        ("{a{b}c}", 0, 6),
    ]
    for test_str, start, expected_pos in test_cases:
        try:
            pos = find_matching_brace(test_str, start)
            if pos == expected_pos:
                print(f"✅ PASS: {test_str!r} from {start} => {pos}")
                passed += 1
            else:
                print(f"❌ FAIL: {test_str!r} from {start}")
                print(f"   Expected: {expected_pos}, Got: {pos}")
                failed += 1
        except Exception as e:
            print(f"❌ FAIL: {test_str!r} - Error: {e}")
            failed += 1

    print()
    print("=" * 70)
    print("TEST 4: extract_frac_arguments")
    print("=" * 70)
    test_cases = [
        (r"\frac{a}{b}", ("a", "b")),
        (r"\frac{a+b}{c}", ("a+b", "c")),
        (r"\frac{x}{y+z}", ("x", "y+z")),
        ("no fracs", None),
    ]
    for input_text, expected in test_cases:
        result = extract_frac_arguments(input_text)
        if expected is None:
            if result is None:
                print(f"✅ PASS: {input_text!r} => None")
                passed += 1
            else:
                print(f"❌ FAIL: {input_text!r}")
                print(f"   Expected: None, Got: {result}")
                failed += 1
        else:
            if result is not None and result[0] == expected[0] and result[1] == expected[1]:
                print(f"✅ PASS: {input_text!r} => {expected}")
                passed += 1
            else:
                print(f"❌ FAIL: {input_text!r}")
                print(f"   Expected: {expected}, Got: {result}")
                failed += 1

    print()
    print("=" * 70)
    print("TEST 5: latex_frac_to_typst_slash")
    print("=" * 70)
    test_cases = [
        (r"\frac{a}{b}", "a/b"),
        (r"\frac{a+b}{c}", "(a+b)/c"),
        (r"\frac{a}{b+c}", "a/(b+c)"),
        (r"\frac{\frac{a}{b}}{c}", "(a/b)/c"),
        ("no fracs here", "no fracs here"),
        (r"text $\frac{1}{2}$ more", r"text $1/2$ more"),
    ]
    for input_text, expected in test_cases:
        result = latex_frac_to_typst_slash(input_text)
        if result == expected:
            print(f"✅ PASS: {input_text!r}")
            passed += 1
        else:
            print(f"❌ FAIL: {input_text!r}")
            print(f"   Expected: {expected!r}")
            print(f"   Got:      {result!r}")
            failed += 1

    print()
    print("=" * 70)
    print("TEST 6: Combined conversion")
    print("=" * 70)
    test_cases = [
        (
            r"这是公式$\frac{a+b}{c}$的例子",
            "这是公式 $(a+b)/c$ 的例子"
        ),
        (
            r"开始$\frac{1}{2}$结束",
            "开始 $1/2$ 结束"
        ),
    ]
    for input_text, expected in test_cases:
        frac_result = latex_frac_to_typst_slash(input_text)
        final_result = add_spacing_around_dollars(frac_result)
        if final_result == expected:
            print(f"✅ PASS: Combined conversion")
            print(f"   Input:  {input_text!r}")
            print(f"   Output: {final_result!r}")
            passed += 1
        else:
            print(f"❌ FAIL: Combined conversion")
            print(f"   Input:    {input_text!r}")
            print(f"   Expected: {expected!r}")
            print(f"   Got:      {final_result!r}")
            failed += 1

    print()
    print("=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)

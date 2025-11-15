import tkinter as tk
from tkinter import scrolledtext
import re
from typing import Tuple, Optional

# --- Configuration Constants ---
CHINESE_CHAR_RANGE = r'[\u4e00-\u9fa5]'
OPERATORS_NEEDING_PARENS = {'+', '-', '*', '/'}
FONT_NAME = "微软雅黑"
FONT_SIZE_LARGE = 12
FONT_SIZE_NORMAL = 10
WINDOW_WIDTH = 650
WINDOW_HEIGHT = 500
TEXT_WIDGET_HEIGHT = 10
TEXT_WIDGET_WIDTH = 80

# --- Core Conversion Logic ---


def add_spacing_around_dollars(text: str) -> str:
    """
    Add a space between adjacent Chinese characters and $ symbols.
    
    Handles two cases:
    1. Chinese character followed by $: "中$" -> "中 $"
    2. $ followed by Chinese character: "$中" -> "$ 中"
    
    Args:
        text: Input text potentially containing Chinese characters and $ symbols.
        
    Returns:
        Text with proper spacing around $ symbols.
    """
    text = re.sub(rf'({CHINESE_CHAR_RANGE})\$', r'\1 $', text)
    text = re.sub(rf'\$({CHINESE_CHAR_RANGE})', r'$ \1', text)
    return text


def find_matching_brace(text: str, start_pos: int) -> int:
    """
    Find the position of the closing brace that matches the opening brace at start_pos.
    
    Args:
        text: The text to search in.
        start_pos: The position of the opening brace (should be '{').
        
    Returns:
        The position of the matching closing brace, or -1 if not found.
        
    Raises:
        ValueError: If start_pos doesn't point to an opening brace.
    """
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
    """
    Extract numerator and denominator from \\frac{...}{...} pattern.
    
    Uses proper nested brace matching instead of greedy regex to handle complex expressions.
    
    Args:
        text: Text potentially containing a \\frac command.
        
    Returns:
        Tuple of (numerator, denominator, end_position) if \\frac found, else None.
    """
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
    """
    Determine if an expression needs to be wrapped in parentheses.
    
    An expression needs parentheses if:
    - It's empty
    - It's not already fully wrapped in balanced parentheses
    - It contains operators that affect precedence (+, -, *, /, or spaces)
    
    Args:
        expression: The expression to check.
        
    Returns:
        True if parentheses are needed, False otherwise.
    """
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
    """
    Recursively convert LaTeX \\frac{numerator}{denominator} to Typst slash format.
    
    Converts:
        \\frac{a}{b} -> a/b
        \\frac{a+b}{c} -> (a+b)/c
        \\frac{\\frac{a}{b}}{c} -> (a/b)/c
    
    Args:
        text: Text potentially containing LaTeX \\frac commands.
        
    Returns:
        Text with all \\frac commands converted to slash format.
    """
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


# --- GUI Application ---

class FracConverterApp:
    """
    A Tkinter GUI application for converting LaTeX fractions and adding spacing in Typst text.
    
    Features:
    - Convert LaTeX \\frac{a}{b} to Typst slash format a/b
    - Add proper spacing between Chinese characters and $ symbols
    - Copy results to clipboard
    """
    
    SAMPLE_TEXT = (
        "这是一个行内公式$f(x)=1$的应用。Typst认为公式$\\frac{a}{b}$是文本的一部分，"
        "因此需要处理与中文的间距。这个公式$\\frac{x+y}{z+1}$也一样。"
    )
    
    def __init__(self, root: tk.Tk) -> None:
        """
        Initialize the application UI.
        
        Args:
            root: The root Tkinter window.
        """
        self.root = root
        self.root.title("Typst 文本处理器 (分数转换 & 中西文空格)")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up all UI components."""
        self._setup_input_section()
        self._setup_button_section()
        self._setup_output_section()

    def _setup_input_section(self) -> None:
        """Create and configure the input text section."""
        input_label = tk.Label(
            self.root,
            text="输入包含 LaTeX 的文本:",
            font=(FONT_NAME, FONT_SIZE_LARGE)
        )
        input_label.pack(pady=(10, 5))

        self.input_text = scrolledtext.ScrolledText(
            self.root,
            height=TEXT_WIDGET_HEIGHT,
            width=TEXT_WIDGET_WIDTH,
            wrap=tk.WORD,
            undo=True,
            font=(FONT_NAME, FONT_SIZE_NORMAL)
        )
        self.input_text.pack(padx=10, expand=True, fill=tk.BOTH)
        self.input_text.insert(tk.END, self.SAMPLE_TEXT)

    def _setup_button_section(self) -> None:
        """Create and configure the button bar."""
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        convert_button = tk.Button(
            button_frame,
            text="转换文本",
            command=self.perform_conversion,
            font=(FONT_NAME, FONT_SIZE_LARGE, "bold"),
            bg="#4CAF50",
            fg="white"
        )
        convert_button.pack(side=tk.LEFT, padx=10)

        copy_button = tk.Button(
            button_frame,
            text="复制结果",
            command=self.copy_to_clipboard,
            font=(FONT_NAME, FONT_SIZE_NORMAL)
        )
        copy_button.pack(side=tk.LEFT, padx=10)

    def _setup_output_section(self) -> None:
        """Create and configure the output text section."""
        output_label = tk.Label(
            self.root,
            text="处理后的 Typst 文本:",
            font=(FONT_NAME, FONT_SIZE_LARGE)
        )
        output_label.pack(pady=(5, 5))

        self.output_text = scrolledtext.ScrolledText(
            self.root,
            height=TEXT_WIDGET_HEIGHT,
            width=TEXT_WIDGET_WIDTH,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=(FONT_NAME, FONT_SIZE_NORMAL)
        )
        self.output_text.pack(padx=10, expand=True, fill=tk.BOTH)

    def perform_conversion(self) -> None:
        """
        Retrieve input text, apply all conversions, and display the result.
        
        Conversion pipeline:
        1. Convert LaTeX \\frac to Typst slash format
        2. Add spacing around $ symbols adjacent to Chinese characters
        """
        original_text = self.input_text.get("1.0", tk.END)
        
        text_after_frac = latex_frac_to_typst_slash(original_text)
        final_text = add_spacing_around_dollars(text_after_frac)
        
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", final_text)
        self.output_text.config(state=tk.DISABLED)

    def copy_to_clipboard(self) -> None:
        """Copy the output text to the system clipboard."""
        result = self.output_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)


if __name__ == "__main__":
    root = tk.Tk()
    app = FracConverterApp(root)
    root.mainloop()

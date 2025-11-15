import tkinter as tk
from tkinter import scrolledtext
import re

# --- 核心转换逻辑 ---

def add_spacing_around_dollars(text):
    """
    在紧邻的中文字符和 $ 符号之间添加一个英文空格。
    """
    # 使用正则表达式来匹配
    # 1. 查找一个中文字符紧跟着一个 $ 符号的情况: ([\u4e00-\u9fa5])\$
    #    替换为: 该中文字符 + 空格 + $
    text = re.sub(r'([\u4e00-\u9fa5])\$', r'\1 $', text)
    
    # 2. 查找一个 $ 符号紧跟着一个中文字符的情况: \$([\u4e00-\u9fa5])
    #    替换为: $ + 空格 + 该中文字符
    text = re.sub(r'\$([\u4e00-\u9fa5])', r'$ \1', text)
    
    return text

def needs_parentheses(expression):
    """
    判断表达式是否因为包含空格或特定运算符而需要加括号。
    """
    expr = expression.strip()
    if not expr:
        return False

    # 1. 检查是否已经被单一最外层括号包裹
    if expr[0] == '(' and expr[-1] == ')':
        balance = 0
        # 找到第一个 '(' 对应的闭合 ')' 的位置
        for i, char in enumerate(expr):
            if char == '(':
                balance += 1
            elif char == ')':
                balance -= 1
                if balance == 0:
                    # 如果这对括号正好包裹整个表达式，则不需要再加
                    if i == len(expr) - 1:
                        return False
                    else:
                        # 例如 (a+b)(c+d) 或 (a+(b))，需要括号
                        break

    # 2. 检查是否包含需要括号的字符
    if any(op in expr for op in ['+', '-', '*', ' ']):
        return True

    return False

def latex_frac_to_typst_slash(text):
    """
    递归地将 LaTeX 的 \\frac{分子}{分母} 格式转换为 Typst 的 斜杠/分数 格式。
    """
    def replacer(match):
        numerator = match.group(1)
        denominator = match.group(2)
        
        numerator = latex_frac_to_typst_slash(numerator)
        denominator = latex_frac_to_typst_slash(denominator)
        
        if needs_parentheses(numerator):
            numerator_str = f"({numerator})"
        else:
            numerator_str = numerator
            
        if needs_parentheses(denominator):
            denominator_str = f"({denominator})"
        else:
            denominator_str = denominator
            
        return f"{numerator_str}/{denominator_str}"

    previous_text = ""
    while "\\frac" in text and text != previous_text:
        previous_text = text
        text = re.sub(r"\\frac\s*\{(.*?)\}\s*\{(.*?)\}", replacer, text)
        
    return text


# --- GUI 应用部分 ---

class FracConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Typst 文本处理器 (分数转换 & 中西文空格)")
        self.root.geometry("650x500")

        # --- 输入部分 ---
        self.input_label = tk.Label(root, text="输入包含 LaTeX 的文本:", font=("微软雅黑", 12))
        self.input_label.pack(pady=(10, 5))

        self.input_text = scrolledtext.ScrolledText(root, height=10, width=80, wrap=tk.WORD, undo=True, font=("微软雅黑", 10))
        self.input_text.pack(padx=10, expand=True, fill=tk.BOTH)
        # 更新了示例文字，以展示新功能
        self.input_text.insert(tk.END, "这是一个行内公式$f(x)=1$的应用。Typst认为公式$\\frac{a}{b}$是文本的一部分，因此需要处理与中文的间距。这个公式$\\frac{x+y}{z+1}$也一样。")

        # --- 按钮框架 ---
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        self.convert_button = tk.Button(button_frame, text="转换文本", command=self.perform_conversion, font=("微软雅黑", 12, "bold"), bg="#4CAF50", fg="white")
        self.convert_button.pack(side=tk.LEFT, padx=10)

        # --- 输出部分 ---
        self.output_label = tk.Label(root, text="处理后的 Typst 文本:", font=("微软雅黑", 12))
        self.output_label.pack(pady=(5, 5))

        self.output_text = scrolledtext.ScrolledText(root, height=10, width=80, wrap=tk.WORD, state=tk.DISABLED, font=("微软雅黑", 10))
        self.output_text.pack(padx=10, expand=True, fill=tk.BOTH)
        
        self.copy_button = tk.Button(button_frame, text="复制结果", command=self.copy_to_clipboard, font=("微软雅黑", 10))
        self.copy_button.pack(side=tk.LEFT, padx=10)

    def perform_conversion(self):
        """获取输入，执行所有转换，并显示结果"""
        # 1. 获取输入框的全部文本
        original_text = self.input_text.get("1.0", tk.END)
        
        # 2. 执行第一项任务：转换LaTeX分数
        text_after_frac = latex_frac_to_typst_slash(original_text)
        
        # 3. 执行第二项任务：在中文和$符号间添加空格
        final_text = add_spacing_around_dollars(text_after_frac)
        
        # 4. 将最终结果显示在输出框
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", final_text)
        self.output_text.config(state=tk.DISABLED)
        
    def copy_to_clipboard(self):
        """复制输出框的内容到剪贴板"""
        result = self.output_text.get("1.0", tk.END).strip()
        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            # 不再显示弹窗


if __name__ == "__main__":
    root = tk.Tk()
    app = FracConverterApp(root)
    root.mainloop()
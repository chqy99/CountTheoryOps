import ply.lex as lex
import config_read

states = (
    ('comment', 'exclusive'),  # 定义一个名为 'comment' 的独占状态
)

tokens = ["Name", "Number", "SciNumber", "Nullptr", "CharPrimary", "StringPrimary"] \
          + config_read.base_tokens

### 忽略 /**/ 的注释状态行为，以及 [] 之间的内容
def t_begin_comment(t):
    r'(/\*|\[)'
    t.lexer.push_state('comment')  # 进入注释状态

def t_comment_end(t):
    r'(\*/|\])'
    t.lexer.pop_state()  # 退出注释状态

def t_comment_content(t):
    r'[^\n]'
    pass

# 注释状态行号要更新
def t_comment_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_comment_ignore = ' \t'
def t_comment_error(t):
    print(f"Illegal character in comment '{t.value[0]}' at line {t.lineno}")
    t.lexer.skip(1)

### 代码状态的行为
# 字面量定义
def t_Number(t):
    r'\d+\.\d*(f)?|\d*\.\d+(f)?|\d+'
    return t

def t_SciNumber(t):
    r'\d+(\.\d+)?[eE][-+]?\d+'
    return t

def t_Nullptr(t):
    r'(nullptr|NULL)'
    return t

def t_CharPrimary(t):
    r"'.'"
    return t

def t_StringPrimary(t):
    r'"(?:\\.|[^"\\])*"'
    return t

# 符号规则
for token_name, token_regex in config_read.symbol_rules.items():
    exec(f"t_{token_regex} = r'{token_name}'")

# 变量标识符
def t_Name(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    if t.value in config_read.ignore_reversed:
        pass
    else:
        t.type = config_read.reversed.get(t.value, 'Name')
        return t

# 行号更新，以便定位错误日志
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# 默认忽略空格符、查表符
t_ignore = ' \t'

# 忽略单行注释
def t_ignore_oneline_comment(t):
    r'\/\/[^\n]*'
    pass

# 错误处理
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex()

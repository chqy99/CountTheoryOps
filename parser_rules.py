import ply.yacc as yacc
import config_read
from lexer_rules import tokens, lexer

# 全局记录每一行的计算量
# 各个语句记录计算量
stmt_theoryOps_store = {}
# 按块记录计算量
block_theoryOps_store = {}
# 控制语句的计算量
control_theoryOps_store = {}

def dict_add_value(dictionary, key, value):
    dictionary[key] = dictionary.setdefault(key, 0) + value

# yacc 通过 docstring 来识别语法
# 动态加载 docstring
def docstring_appender(docstr):
    def decorator(func):
        func.__doc__ = docstr
        return func
    return decorator

# 项及上层语法只记录计算量
# 项内用元组记录，第一个为计算量，第二个为原始的 token（区分符号减）

# 定义程序入口规则，第一个函数默认为入口规则
def p_stmts(p):
    '''stmts : stmt_link
             | stmts stmt_link'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = (p[1][0] + p[2][0], p[2][1])

def p_stmts1(p):
    '''stmts : stmt_nolink
             | stmts stmt_nolink'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        if p[1][0] != 0:
            global block_theoryOps_store
            dict_add_value(block_theoryOps_store, p[1][1], p[1][0])
        p[0] = p[2]

def p_domain_name(p):
    '''domain_name : Name DOUBLECOLON Name'''

# 函数名，非函数调用
# TODO: c++ 变量声明语法复杂，目前有规则冲突
def p_func_name(p):
    '''func_name : dtype Name LPAREN RPAREN
                 | dtype Name LPAREN declare_name RPAREN
                 | dtype Name LPAREN declares_name RPAREN
                 | dtype domain_name LPAREN RPAREN
                 | dtype domain_name LPAREN declare_name RPAREN
                 | dtype domain_name LPAREN declares_name RPAREN
                 | dtype TIMES Name LPAREN RPAREN
                 | dtype TIMES Name LPAREN declare_name RPAREN
                 | dtype TIMES Name LPAREN declares_name RPAREN
                 | dtype TIMES domain_name LPAREN RPAREN
                 | dtype TIMES domain_name LPAREN declare_name RPAREN
                 | dtype TIMES domain_name LPAREN declares_name RPAREN'''
    p[0] = 0

def p_block(p):
    '''block : LBRACE stmts RBRACE
             | LBRACE RBRACE'''
    if len(p) == 4:
        p[0] = p[2][0]
        global block_theoryOps_store
        dict_add_value(block_theoryOps_store, p.slice[3].lineno - 1, p[0])
    else:
        p[0] = 0

# 语句
def p_stmt(p):
    '''stmt : stmt_link
            | stmt_nolink'''
    p[0] = p[1]

# 计算量累计语句，返回计算量和行号
def p_stmt_link(p):
    '''stmt_link : expr_stmt
                 | declare_stmt'''
    p[0] = p[1]

# 计算量隔断语句
def p_stmt_nolink(p):
    '''stmt_nolink : block
                   | if_stmt
                   | while_stmt
                   | dowhile_stmt
                   | for_stmt
                   | switch_stmt
                   | BREAK SEMICOLON
                   | CONTINUE SEMICOLON
                   | RETURN SEMICOLON
                   | RETURN expr SEMICOLON
                   | SEMICOLON
                   | func_name'''
    p[0] = (0, 0)

def p_if_stmt(p):
    '''if_stmt : IF LPAREN expr RPAREN stmt
               | ELSE stmt'''
    global control_theoryOps_store
    if len(p) == 6:
        dict_add_value(control_theoryOps_store, p.slice[4].lineno, p[3])
        p[0] = p[3] + p[5][0]
    else:
        p[0] = p[2][0]

def p_switch_stmt(p):
    '''switch_stmt : SWITCH LPAREN expr RPAREN LBRACE switch_contents RBRACE'''
    p[0] = p[3] + p[6]

def p_switch_content(p):
    '''switch_content : CASE term COLON stmt
                      | DEFAULT COLON stmt'''
    if len(p) == 5:
        global control_theoryOps_store
        dict_add_value(control_theoryOps_store, p.slice[3].lineno, p[2][0])
        p[0] = p[2][0] + p[4][0]
    else:
        p[0] = p[3][0]

def p_switch_contents(p):
    '''switch_contents : switch_content
                       | switch_contents switch_content'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[1] + p[2]

def p_while_stmt(p):
    '''while_stmt : WHILE LPAREN expr RPAREN block'''
    global control_theoryOps_store
    dict_add_value(control_theoryOps_store, p.slice[4].lineno, p[3])
    p[0] = p[3] + p[5]

def p_dowhile_stmt(p):
    '''dowhile_stmt : DO block WHILE LPAREN expr RPAREN'''
    global control_theoryOps_store
    # do while 在 while 上一行加计算量
    dict_add_value(control_theoryOps_store, p.slice[3].lineno - 1, p[5])
    p[0] = p[5] + p[2]

def p_for_expr(p):
    '''for_expr : exprs
                | expr
                | declare_name
                | declare_names
                | declares_name
                | '''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = 0

def p_for_stmt(p):
    '''for_stmt : FOR LPAREN for_expr SEMICOLON for_expr SEMICOLON for_expr RPAREN block'''
    global control_theoryOps_store
    p[0] = p[3] + p[5] + p[7]
    dict_add_value(control_theoryOps_store, p.slice[8].lineno, p[0])
    p[0] += p[9]

def p_declare_stmt(p):
    '''declare_stmt : declare_name SEMICOLON
                    | declare_names SEMICOLON
                    | declares_name SEMICOLON'''
    global stmt_theoryOps_store
    dict_add_value(stmt_theoryOps_store, p.slice[2].lineno, p[1])
    p[0] = (p[1], p.slice[2].lineno)

# 类型相关
dtype_docstring = "dtype : "
for key, value in config_read.base_config["dtype"].items():
    dtype_docstring += value + "\n| "

@docstring_appender(dtype_docstring[:-3])
def p_dtype(p):
    p[0] = 0

# 逗号连接多个类型
def p_dtypes(p):
    '''dtypes : dtype COMMA dtype
              | dtypes COMMA dtype'''
    p[0] = 0

# 单个变量声明
def p_declare_name(p):
    '''declare_name : dtype term
                    | dtype expr_assign'''
    if isinstance(p[2], tuple):
        p[0] = p[2][0]
    else:
        p[0] = p[2]

# 同类型单个变量声明（逗号分割）
def p_declare_names(p):
    '''declare_names : declare_name COMMA term
                     | declare_name COMMA expr_assign
                     | declare_names COMMA term
                     | declare_names COMMA expr_assign'''
    if isinstance(p[3], tuple):
        p[0] = p[1] + p[3][0]
    else:
        p[0] = p[1] + p[3]

# 不同类型单个变量声明（逗号分割）
def p_declares_name(p):
    '''declares_name : declare_name COMMA declare_name
                     | declares_name COMMA declare_name'''
    p[0] = p[1] + p[3]

# 表达式语句
def p_expr_stmt(p):
    '''expr_stmt : expr SEMICOLON
                 | exprs SEMICOLON'''
    global stmt_theoryOps_store
    dict_add_value(stmt_theoryOps_store, p.slice[2].lineno, p[1])
    p[0] = (p[1], p.slice[2].lineno)

# 单个表达式
def p_expr(p):
    '''expr : expr_assign
            | expr_opassign
            | expr_binary
            | expr_ternary'''
    p[0] = p[1]

# 多个逗号连接的表达式
def p_exprs(p):
    '''exprs : expr COMMA expr
             | exprs COMMA expr'''
    p[0] = p[1] + p[3]

def p_expr_assign(p):
    '''expr_assign : term ASSIGN expr'''
    p[0] = p[1][0] + p[3]

opassign_docstring = "expr_opassign : "
for key, value in config_read.base_config["opassign"].items():
    opassign_docstring += "term " + value + " expr\n| "

@docstring_appender(opassign_docstring[:-3])
def p_expr_opassign(p):
    p[0] = p[1][0] + p[3] + 2

# 三元运算
# TODO: 把条件
def p_expr_ternary_op(p):
    '''expr_ternary : expr_binary QUESTION expr_binary COLON expr_binary'''
    p[0] = p[1] + (p[3] + p[5]) / 2

# 双元运算
def p_expr_binary_op(p):
    '''expr_binary : term'''
    p[0] = p[1][0]

# 计算量为 1 的双元运算
binary_op_docstring = "expr_binary : "
for key, value in config_read.base_config["binary_operator"].items():
    binary_op_docstring += "expr_binary " + value + " term\n| "
@docstring_appender(binary_op_docstring[:-3])
def p_expr_binary_op1(p):
    p[0] = p[1] + p[3][0] + 1

# 计算量为 0 的双元运算
binary_op_docstring = "expr_binary : "
for key, value in config_read.base_config["comp_operator"].items():
    binary_op_docstring += "expr_binary " + value + " term\n| "
@docstring_appender(binary_op_docstring[:-3])
def p_expr_binary_op2(p):
    p[0] = p[1] + p[3][0]

# 项定义
def p_term(p):
    '''term : LPAREN dtype RPAREN term
            | unary'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = (p[4][0] + 1, p[4][1])

# 前置运算符
# 符号加，取地址和解引用的计算量均视为 0
def p_unary(p):
    '''unary : postfix
             | PLUS term
             | TIMES term
             | BITAND term'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = p[2]

# 符号减，非，反的计算量：数字为 0，变量为 1
def p_unary1(p):
    '''unary : MINUS term
             | NOT term
             | BITNOT term'''
    if p[2][1] == 'Number' or p[2][1] == 'SciNumber':
        p[0] = p[2]
    else:
        p[0] = (p[2][0] + 1, p[2][1])

def p_unary2(p):
    '''unary : INCREMENT term
             | DECREMENT term'''
    p[0] = (p[2][0] + 2, p[2][1])

# sizeof, typeId 特殊运算符
def p_unary3(p):
    '''unary : SIZEOF LPAREN dtype RPAREN
             | SIZEOF LPAREN term RPAREN
             | TYPEID LPAREN term RPAREN'''
    if isinstance(p[3], tuple):
        p[0] = p[3]
    else:
        p[0] = (0, 'sizeof')

# 解析 <> 之间的内容
def p_between_angle_bracket(p):
    '''between_angle_bracket : LT dtype GT
                             | LT dtypes GT'''
    p[0] = 0

# 解析 cast 特殊运算符
def p_unary4(p):
    '''unary : DYNAMICCAST between_angle_bracket LPAREN expr_binary RPAREN
             | STATICCAST between_angle_bracket LPAREN expr_binary RPAREN
             | REINTERPRETCAST between_angle_bracket LPAREN expr_binary RPAREN
             | CONSTCAST between_angle_bracket LPAREN expr_binary RPAREN'''
    p[0] = (p[4] + 1, 'cast')

# 后置运算符
def p_postfix(p):
    '''postfix : primary
               | postfix DOT Name
               | postfix ARROW Name'''
    p[0] = p[1]

def p_postfix1(p):
    '''postfix : postfix INCREMENT
               | postfix DECREMENT'''
    p[0] = (p[1][0] + 3, p[1][1])

# 函数调用运算量视为 1
def p_postfix2(p):
    '''postfix : postfix LPAREN RPAREN
               | postfix LPAREN expr RPAREN
               | postfix LPAREN exprs RPAREN'''
    if len(p) == 4:
        p[0] = (p[1][0] + 1, p[1][1])
    else:
        p[0] = (p[1][0] + p[3] + 1, p[1][1])

# 字面量
def p_primary(p):
    '''primary : Number
               | SciNumber
               | Nullptr
               | CharPrimary
               | StringPrimary
               | Name
               | domain_name
               | LPAREN expr RPAREN'''
    # TODO: Name, domain_name 函数对应的计算量
    if len(p) == 2:
        p[0] = (0, str(p.slice[1].type))
    else:
        p[0] = (p[2], 'expr')

# 语法分析器错误处理
def p_error(p):
    if p:
        print("Syntax error at token", p.type, "value", p.value, "line", p.lineno)
        # 无法识别的直接跳过
        yacc.errok()
    else:
        print("Syntax error at EOF")

parser = yacc.yacc()

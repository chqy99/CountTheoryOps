from lexer_rules import lexer
from parser_rules import parser

# 具体算子 cpuCompute 路径，只支持单文件检查，不能文件跳转
count_file_path = '/home/cambricon/vscode/TestCode/code1.c++'
with open(count_file_path, 'r', encoding='utf-8') as file:
        all_lines = file.readlines()
# 扫描 [// count_ops_begin, // count_ops_end] 之间的文件
# 可以注释掉不想统计计算量的部分
codeLines = []
flag = 0
for line in all_lines:
    if "// count_ops_begin" in line:
        flag = 1
    elif "// count_ops_end" in line:
        flag = 0
        codeLines.append("\n")

    if flag == 1:
        codeLines.append(line)

# 合并行
code = ""
for item in codeLines:
    code += item

# 语法解析，解析完后会把结果存储到 theoryOps_store 中
parser.parse(code, lexer)

# 显示状态，0 为不显示，1 为以注释显示，2 为以代码显示
def show_theoryOps(stmt_show = 2, block_show = 0, control_show = 0):
    from parser_rules import stmt_theoryOps_store, \
                             block_theoryOps_store, \
                             control_theoryOps_store
    # 逐语句和逐块不能同时以代码显示
    assert(not(stmt_show == 2 and block_show == 2))
    block_show += 3
    control_show += 6
    show_ops_count = []
    if stmt_show > 0:
        for key in stmt_theoryOps_store:
            show_ops_count.append([key, stmt_theoryOps_store[key], stmt_show])

    if block_show % 3 > 0:
        for key in block_theoryOps_store:
            show_ops_count.append([key, block_theoryOps_store[key], block_show])

    if control_show % 3 > 0:
        for key in control_theoryOps_store:
            show_ops_count.append([key, control_theoryOps_store[key], control_show])

    show_ops_count = sorted(show_ops_count, key=lambda x: x[0], reverse=True)
    return show_ops_count

for item in show_theoryOps():
    if item[1] == 0:
        continue
    if item[2] == 1:
        insert_str = "// last stmt: theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)
    elif item[2] == 2:
        insert_str = "/* last stmt */ theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)
    elif item[2] == 4:
        insert_str = "// cur block: theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)
    elif item[2] == 5:
        insert_str = "/* cur block */ theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)
    elif item[2] == 7:
        insert_str = "// cur control: theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)
    elif item[2] == 8:
        insert_str = "/* cur control */ theory_ops_ += " + str(item[1]) + ";\n"
        codeLines.insert(item[0], insert_str)

# 按当前时间输出文件
from datetime import datetime
current_time = datetime.now()
output_name = current_time.strftime("%Y-%m-%d-%H:%M") + ".cpp"
with open(output_name, 'w', encoding='utf-8') as file:
    file.writelines(codeLines)

# 调用 clang-format 刷新对齐格式
import subprocess
clang_format_command = [
    'clang-format',
    '-style={BasedOnStyle: google, PointerAlignment: Right, \
             SortIncludes: false, ColumnLimit: 80}',
    '-i',
    output_name
]
subprocess.run(clang_format_command, check=True)

#!/usr/bin/env python3
"""
检查Mongo_Reader.py文件中的语法错误并报告
"""
import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试解析AST
        ast.parse(content)
        print(f"✅ {filename} 语法检查通过")
        return True
    except SyntaxError as e:
        print(f"❌ {filename} 语法错误:")
        print(f"   行号: {e.lineno}")
        print(f"   列号: {e.offset}")
        print(f"   错误: {e.msg}")
        if e.text:
            print(f"   问题行: {e.text.strip()}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    check_syntax("Mongo_Reader.py")

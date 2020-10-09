# -*- coding: utf-8 -*-
'''
Copyright 2020, Ainstein Inc. All Rights Reserved


 THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 '''
import sys
import os
import re
import subprocess

# 翻译步骤：
# 1，执行脚本Translate.py，翻译所有.ui文件里的中文
# 2，执行脚本pyside2translate.py，翻译所有.py文件里的用self.tr括起来的中文

# ============脚本详细解释================
#     PyQt5版本的Qt语言家的lupdate只支持打开.ui文件或Qt Designer创建的.pro文件，
# 如果用户在Qt Designer工程外又手动编写代码，增加了新的ui界面，因为lupdate无法打
# 开.py文件，也就无法读取用户自己编写的界面代码里的字符串来进行翻译。
#     而PySide2版本的Qt语言家的pyside2-lupdate可以打开.py文件进行扫描查找其中的
# tr()来进行翻译，而且PySide2版本的lrelease生成的qm文件格式和PyQt5的兼容，因此本
# 工程做了两个qm文件：
# xx_cus.qm文件是PySide2的pyside2-lupdate生成的.ts文件生成的；
# xx_ui.qm文件是PyQt5的lupdate生成的.ts文件生成的。
#     执行脚本pyside2translate.py，可生成xx_cus.qm文件；执行脚本Translate.py，可
# 生成xx_ui.qm文件
#     但是由于PySide2版本的linguist有bug，导致linguist打开.ts文件之后，界面里的中
# 文字符串都是乱码，因此在所有用户自定义界面代码里的字符串不能用self.tr()函数
# 解决方案一：用self.trUtf8()，这样linguist才会正确显示汉字，但是在PyQt5里已经不
# 存在trUtf8()# 函数了，trUtf8()只是用来骗过PySide2版本的linguist，让他正确显示汉
# 字而已。因此最后# 还要把所有trUtf8()再改回到tr()
# 解决方案二：自动生成一个.pro文件，在文件中填写文件参数CODECFORTR可设置tr编码，此
# 方法不需要修改源代码中的tr()函数，并且在语言家界面还可以正确显示对应源码，但是
# linguist会在翻译完之后保存的时候自动把ts文件里所有的encoding="UTF-8"去掉，这会导
# 致下一次lupdate在更新ts文件的时候产生乱码。
# 因此脚本建立了两个ts文件，pyside2-lupdate生成的是带有encoding="UTF-8"的en_cus_o.ts
# 文件，此文件被脚本处理，去掉encoding="UTF-8"后生成dest_en文件被linguist读取后翻译发
# 布，pyside2-lupdate在生成en_cus_o.ts之前，先将原来的dest_en文件加入encoding="UTF-8"
# 后覆盖en_cus_o.ts，这样pyside2-lupdate就可以正常更新


def creat_pro(work_dir, dest_en):
    os.system('echo CODECFORTR = UTF-8>a.pro')
    os.system('>>a.pro set /p="SOURCES = " <nul')  # 清空或创建
    for travel in os.walk(work_dir):
        folder = travel[0] + '\\'
        files = travel[2]
        for file in files:
            if os.path.splitext(file)[-1] == '.py':
                source = folder + file
                os.system('>>a.pro set /p=" ' + source + ' " <nul')
                # source += ' ' + folder + file
    os.system('echo.>>a.pro')
    os.system('echo TRANSLATIONS = ' + dest_en + '>>a.pro')


def convert_utf8_to_normal_context(dest_en_orig, dest_en):
    try:
        file1 = open(dest_en_orig, 'r', encoding='utf-8')
        file2 = open(dest_en, 'w', encoding='utf-8')
        for line in file1.readlines():
            # num = re.sub(r'<message encoding="UTF-8">$', '<message>', line, 0, re.U)
            num = re.sub(r'<context encoding="UTF-8">$', '<context>', line, 0, re.U)
            file2.write(num)
        file1.close()
        file2.close()
    except Exception as e:
        print(str(e))
        exit()


def convert_utf8_to_normal_message(dest_en_orig, dest_en):
    try:
        file1 = open(dest_en_orig, 'r', encoding='utf-8')
        file2 = open(dest_en, 'w', encoding='utf-8')
        for line in file1.readlines():
            num = re.sub(r'<message encoding="UTF-8">$', '<message>', line, 0, re.U)
            # num = re.sub(r'<context encoding="UTF-8">$', '<context>', line, 0, re.U)
            file2.write(num)
        file1.close()
        file2.close()
    except Exception as e:
        print(str(e))
        exit()


def convert_normal_context_to_utf8(dest_en_orig, dest_en):
    try:
        file1 = open(dest_en_orig, 'r', encoding='utf-8')
        file2 = open(dest_en, 'w', encoding='utf-8')
        for line in file1.readlines():
            # num = re.sub(r'<message encoding="UTF-8">$', '<message>', line, 0, re.U)
            num = re.sub(r'<context>$', '<context encoding="UTF-8">', line, 0, re.U)
            file2.write(num)
        file1.close()
        file2.close()
    except Exception as e:
        print(str(e))
        exit()


def convert_normal_message_to_utf8(dest_en_orig, dest_en):
    try:
        file1 = open(dest_en_orig, 'r', encoding='utf-8')
        file2 = open(dest_en, 'w', encoding='utf-8')
        for line in file1.readlines():
            num = re.sub(r'<message>$', '<message encoding="UTF-8">', line, 0, re.U)
            # num = re.sub(r'<context encoding="UTF-8">$', '<context>', line, 0, re.U)
            file2.write(num)
        file1.close()
        file2.close()
    except Exception as e:
        print(str(e))
        exit()


py_path = os.path.dirname(sys.executable)
py_site_path = py_path + '\\Lib\\site-packages'
py_side2_path = py_site_path + '\\PySide2'
py_QTtool_path = py_site_path + '\\pyqt5_tools\\Qt\\bin'

work_dir = os.path.abspath('..\\')

lupdate = py_side2_path + '\\pyside2-lupdate '
linguist = py_side2_path + '\\linguist '
# linguist = py_QTtool_path + '\\linguist'
lrelease = py_side2_path + '\\lrelease '

source = ''
dest = work_dir + '\\Language'
if not os.path.exists(dest):
    os.mkdir(os.path.dirname(dest))

qm_dest_cn = ' ' + dest + '\\zh_CN_cus.qm'
dest_cn = ' ' + dest + '\\zh_CN_cus.ts'

qm_dest_en = dest + '\\en_cus.qm'
dest_en = dest + '\\en_cus.ts'
tmp_file = dest + '\\en_cus_tmp.ts'
dest_en_orig = dest + '\\en_cus_o.ts'
tmp_o_file = dest + '\\en_cus_o_tmp.ts'
creat_pro(work_dir, dest_en_orig)

convert_normal_context_to_utf8(dest_en, tmp_file)
convert_normal_message_to_utf8(tmp_file, dest_en_orig)
subprocess.call(lupdate + ' ' + dest + '\\a.pro' + ' -noobsolete')

convert_utf8_to_normal_context(dest_en_orig, tmp_o_file)  # 去掉encoding="UTF-8"
convert_utf8_to_normal_message(tmp_o_file, dest_en)
subprocess.call(linguist + dest_en)

os.remove(dest + '\\a.pro')
os.remove(dest_en_orig)
os.remove(tmp_file)
os.remove(tmp_o_file)

subprocess.call(lrelease + dest_en + ' -qm ' + qm_dest_en)

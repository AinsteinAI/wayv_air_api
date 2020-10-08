# -*- coding: utf-8 -*-
import sys
import os
import subprocess

py_path = os.path.dirname(sys.executable)
py_site_path = py_path + '\\Lib\\site-packages'
py_QTtool_path = py_site_path + '\\pyqt5_tools\\Qt\\bin'

work_dir = os.path.abspath('..\\')

lupdate = py_QTtool_path + '\\lupdate'
linguist = py_QTtool_path + '\\linguist'
lrelease = py_QTtool_path + '\\lrelease'

source = ''
dest = work_dir + '\\Language'
if not os.path.exists(dest):
    os.mkdir(os.path.dirname(dest))

qm_dest_cn = ' ' + dest + '\\zh_CN_ui.qm'
dest_cn = ' ' + dest +'\\zh_CN_ui.ts'

qm_dest_en = ' ' + dest + '\\en_ui.qm'
dest_en = ' ' + dest +'\\en_ui.ts'

for travel in os.walk(work_dir):
    folder = travel[0] + '\\'
    files = travel[2]
    for file in files:
        if os.path.splitext(file)[-1] == '.ui':
            source += ' ' + folder + file

# -no-obsolete意思是不更新废弃代码，源文件里和ts文件里对应位置相关信息不一致的代码（比如被注释掉了，类型不一致等等）
subprocess.call(lupdate + source + ' -no-obsolete -ts' + dest_en)
subprocess.call(linguist + dest_en)
subprocess.call(lrelease + dest_en + ' -qm' + qm_dest_en)

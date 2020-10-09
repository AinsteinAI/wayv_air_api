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
from PyQt5.QtCore import QObject, QTranslator, QLocale
from pathlib import Path


class Translator(QObject):
    def __init__(self):
        super(Translator, self).__init__()
        self._sys_base_qm = QTranslator()
        self._ui_qm = QTranslator()  # for ui created by Qt designer
        self.cus_ui_qm = QTranslator()  # for ui created by hand
        self.local_language = QLocale.English

    def refresh_language(self, app):
        self.load_language(app, QLocale.system().language())

    def load_language(self, app, language):
        app.removeTranslator(self._sys_base_qm)
        app.removeTranslator(self._ui_qm)
        app.removeTranslator(self.cus_ui_qm)

        if language == QLocale.Chinese:
            tmp_path = Path('Language/qt_zh_CN.qm')
            self._sys_base_qm.load(str(tmp_path))
            tmp_path = Path('Language/zh_CN_ui.qm')
            self._ui_qm.load(str(tmp_path))
            tmp_path = Path('Language/zh_CN_cus.qm')
            self.cus_ui_qm.load(str(tmp_path))
        elif language == QLocale.English:
            tmp_path = Path('Language/qt_en.qm')
            self._sys_base_qm.load(str(tmp_path))
            tmp_path = Path('Language/en_ui.qm')
            self._ui_qm.load(str(tmp_path))
            tmp_path = Path('Language/en_cus.qm')
            self.cus_ui_qm.load(str(tmp_path))
        else:
            self._sys_base_qm = QTranslator()
            self._ui_qm = QTranslator()
            self.cus_ui_qm = QTranslator()

        app.installTranslator(self._sys_base_qm)
        app.installTranslator(self._ui_qm)
        app.installTranslator(self.cus_ui_qm)


global_translator = Translator()

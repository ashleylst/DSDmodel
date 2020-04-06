import sys
import os
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QPixmap
from src import model, graph_processor, processorthread, uiwindow


class MyWindow(QMainWindow, uiwindow.Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyWindow, self).__init__(parent)
        self.model = model.Model()
        self.procthread = None
        self.lock = None
        self.simuarg = None
        self.paused = False
        self.setupUi(self)

    def refresh(self):
        self.lineEdit.setText(self.model.get_filename())
        self.textEdit.setText(self.model.get_filecontents())

    def returnPressedSlot(self):
        fname = self.lineEdit.text()
        if self.model.is_valid(fname):
            self.model.set_filename(self.lineEdit.text())
            self.refresh()
        else:
            m = QtWidgets.QMessageBox()
            m.setText("Invalid file name!\n" + fname)
            m.setIcon(QtWidgets.QMessageBox.Warning)
            m.setStandardButtons(QtWidgets.QMessageBox.Ok
                                 | QtWidgets.QMessageBox.Cancel)
            m.setDefaultButton(QtWidgets.QMessageBox.Cancel)
            ret = m.exec_()
            self.lineEdit.setText("")
            self.refresh()

    def browseSlot(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fname, filetype = QtWidgets.QFileDialog.getOpenFileName(self,
                                                          "Select File",
                                                          "./",
                                                          "All Files (*);;Text Files (*.txt)")
        if fname:
            self.debugPrint("setting file name: " + fname)
            self.model.set_filename(fname)
            self.refresh()

    def submitSlot(self):
        # Take care of submitting more than once
        if self.procthread:
            if self.procthread.is_alive():
                self.procthread.stop()

        text = self.textEdit.toPlainText()

        if self.model.get_filename() is None:
            if text == '':
                m = QtWidgets.QMessageBox()
                m.setText("Please provide an input to submit.\n")
                m.setIcon(QtWidgets.QMessageBox.Warning)
                m.setStandardButtons(QtWidgets.QMessageBox.Ok)
                m.setDefaultButton(QtWidgets.QMessageBox.Ok)
                ret = m.exec_()
                return
            else:
                m = QtWidgets.QMessageBox()
                m.setText("Do you want to save the input?\n")
                m.setIcon(QtWidgets.QMessageBox.Warning)
                m.setStandardButtons(QtWidgets.QMessageBox.Ok
                                     | QtWidgets.QMessageBox.Cancel)
                m.setDefaultButton(QtWidgets.QMessageBox.Ok)
                ret = m.exec_()
                if ret == m.Ok:
                    try:
                        os.mkdir('./input')
                    except FileExistsError:
                        pass
                    file = open('./input/your_input.txt', 'w+')
                    file.write(text)
                    file.close()
                    self.model.set_filename('./input/your_input.txt')

        elif self.model.get_filecontents() != text:
            m = QtWidgets.QMessageBox()
            m.setText("Do you want to save the change to input file?\n")
            m.setIcon(QtWidgets.QMessageBox.Warning)
            m.setStandardButtons(QtWidgets.QMessageBox.Ok
                                 | QtWidgets.QMessageBox.Cancel)
            m.setDefaultButton(QtWidgets.QMessageBox.Ok)
            ret = m.exec_()
            if ret == m.Ok:
                file = open(self.model.fileName, 'w+')
                file.write(self.textEdit.toPlainText())
                file.close()
                self.model.set_filename(self.model.fileName)

        self.debugPrint("Submitted File")
        info, initnames, concentrations, outdir, simupara, initlen = graph_processor.initiation(text=text)
        self.simuarg = (initnames, concentrations, outdir, simupara, initlen)
        self.procthread = processorthread.ProcessorThread(args=info)
        self.procthread.setDaemon(True)
        self.lock = self.procthread.get_lock()
        self.paused = False
        self.procthread.start()

    def pauseSlot(self):
        if not self.procthread or self.paused:
            return
        print("need to pause")
        self.lock.acquire()
        self.procthread.pause()
        self.paused = True

    def resumeSlot(self):
        if not self.procthread:
            return
        print("need to resume")
        if self.lock.locked():
            self.lock.release()
        self.procthread.resume()
        self.paused = False

    def stopSlot(self):
        if not self.procthread:
            return
        if not self.paused:
            self.lock.acquire()
        self.procthread.stop()

    def showSlot(self):
        if not self.procthread:
            return
        specieslist, speciesidmap, reactionlist, kinetics, indexlist, cursor, visited = self.procthread.get_arg_info()
        initnames, concentrations, outdir, simupara, initlen = self.simuarg
        graph_processor.post_enumeration(specieslist, reactionlist, initlen, initnames, concentrations, outdir, simupara)
        self.display_output_txt(outdir+'/output.txt')
        self.display_output_img(outdir + '/simres.png')

    def debugPrint(self, msg):
        self.debugTextBrowser.append(msg)

    def display_output_txt(self, fname):
        self.reneTextBrowser.setText(open(fname, 'r').read())
        # self.textBrowser.append(open(fname, 'r').read())

    def display_output_img(self, fname):
        pixmap = QPixmap(fname)
        self.imageLabel.setPixmap(pixmap)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    myWin = MyWindow()
    myWin.setWindowTitle('DSDPy GUI')
    myWin.show()
    sys.exit(app.exec_())

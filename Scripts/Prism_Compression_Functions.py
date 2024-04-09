from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import zipfile,tarfile, os, traceback, re

from PrismCore import PrismCore
from ProjectScripts import SceneBrowser

CompressionZipType = {
    "ZIP_STORED" : 0,
    "ZIP_DEFLATED" : 8,
    "ZIP_BZIP2" : 12,
    "ZIP_LZMA" : 14
}

class pluginSignals(QObject):
    updateUI = Signal()
    taskFinished = Signal()
    updateProgress = Signal(str)
    errorPopup = Signal(str)   

class CompressionTaskSignals(QObject):
    doAll = Signal(str)
    doAllButLatest = Signal(str)
    doCustom = Signal(str,int, int)

class workerThread(QThread):
    signals = None
    filePath = None
    fileList = None
    
    def __init__(self, signals:pluginSignals, compressionType = 'Zip', deleteOld= True, zipCompressionLevel = 8, filePath:str=None, fileList = None):        
        super(workerThread, self).__init__()
        
        self.compressionType = compressionType
        self.zipCompressionLevel = zipCompressionLevel
        self.deleteOld = deleteOld
        
        if filePath is None and fileList is None:
                self.signals.errorPopup.emit("Both filePath and fileList cannot be None")
                workerThread.terminate()
        
        if filePath is not None:
            self.path = filePath
        else:
            self.path = ""
            
        if fileList is not None:
            self.fileList = fileList
        
        self.signals = signals
        
        if compressionType != 'Zip' and compressionType != 'Tar.gz':
            self.signals.errorPopup.emit("Invalid compression type")
            return
        
    def compressFile(self, file:str):
        
        if os.path.exists(file):
            try:
                if self.compressionType == 'Zip':
                    with zipfile.ZipFile(file.removesuffix(os.path.splitext(file)[1]) + ".zip", "w", zipfile.ZIP_DEFLATED) as zip_ref:
                        zip_ref.write(file, os.path.basename(file))
                        
                if self.compressionType == 'Tar.gz':
                    with tarfile.open(file.removesuffix(os.path.splitext(file)[1]) + ".tar.gz", "w:gz") as tar_ref:
                        tar_ref.add(file, os.path.basename(file))
                
            except Exception as e:
                self.signals.errorPopup.emit(f"Error decompressing file \n {traceback.format_exception(e)}")
                return
            try:
                # validate the zip file
                if self.compressionType == 'Zip':
                    with zipfile.ZipFile(file.removesuffix(os.path.splitext(file)[1]) + ".zip", 'r') as zip_ref:
                        if zip_ref.testzip() is None:
                            if self.deleteOld:
                                os.remove(file)
                            self.signals.updateUI.emit()
                            return
                        else:
                            self.signals.errorPopup.emit("Error compressing file")
                            return
                if self.compressionType == 'Tar.gz':
                    with tarfile.open(file.removesuffix(os.path.splitext(file)[1]) + ".tar.gz", 'r:gz') as tar_ref:
                        if tar_ref.getnames() is not None:
                            if self.deleteOld:
                                os.remove(file)
                            
                            #TODO: Prism does not fully support multi extension files, figure out a way to rename/copy versioninfo.json file
                            
                            self.signals.updateUI.emit()
                            return
                        else:
                            self.signals.errorPopup.emit("Error compressing file")
                            return
            except Exception as e:
                self.signals.errorPopup.emit(f"Error decompressing file \n {traceback.format_exception(e)}")
        return

    def decompressFile(self, file:str):
        unzipped_file = None
        try:
            if self.path.endswith(".zip"):
                # decompress filepath
                with zipfile.ZipFile(file, 'r') as zip_ref:
                    unzipped_files = zip_ref.namelist()
                    zip_ref.extractall(os.path.dirname(file))

            elif self.path.endswith(".tar.gz"):
                # decompress filepath
                with tarfile.open(file, 'r:gz') as tar_ref:
                    unzipped_files = tar_ref.getnames()
                    tar_ref.extractall(os.path.dirname(file))

            allFilesExtracted = True

            for unzipped_file in unzipped_files:
                if os.path.exists(os.path.join(os.path.dirname(file), unzipped_file)):
                    continue
                else:
                    allFilesExtracted = False
                    break
            
            if allFilesExtracted:
                if self.deleteOld:
                    os.remove(self.path)
            else:
                self.signals.errorPopup.emit("Error decompressing file, uncompressed file not found")
                         
        except Exception as e:
            self.signals.errorPopup.emit(f"Error decompressing file \n {traceback.format_exception(e)}")

    def run(self):
        #TODO: separate logic for compressing and decompressing
        if os.path.exists(self.path):
            if os.path.isfile(self.path):
                if not self.path.endswith(".zip") and not self.path.endswith(".tar.gz"):
                    self.compressFile(self.path)
                else:
                    self.decompressFile(self.path)
                
        elif self.fileList is not None and len(self.fileList) > 0:
            for file in self.fileList:
                self.signals.updateProgress.emit(f"Compressing {os.path.basename(file)}... Will close when completed.")
                self.compressFile(file)
                    
        self.signals.taskFinished.emit()
        self.signals.updateUI.emit()

class CompressingPopup(QDialog):
    def __init__(self, parent=None):
        super(CompressingPopup, self).__init__(parent)
        self.setWindowTitle("Compressing file")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.label = QLabel("Compressing file... Will close when completed.")
        self.mainLayout.addWidget(self.label)

class CompressionTask(QDialog):

    def __init__(self, signals:CompressionTaskSignals, path:str, parent=None):
        super(CompressionTask, self).__init__(parent)
        
        self.TaskPath = path
        self.signals = signals
        
        self.setWindowTitle("Compressing a Task")
        self.mainLayout = QVBoxLayout()
        self.setLayout(self.mainLayout)
        
        self.radioBtnLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.radioBtnLayout)
        
        self.allRadioBtn = QRadioButton("All")
        self.allRadioBtn.setChecked(True)
        self.radioBtnLayout.addWidget(self.allRadioBtn)
        
        self.allButLatestRadioBtn = QRadioButton("All but latest")
        self.radioBtnLayout.addWidget(self.allButLatestRadioBtn)
        
        self.customRadioBtn = QRadioButton("Custom")
        self.radioBtnLayout.addWidget(self.customRadioBtn)
        
        self.radioBtnGroup = QButtonGroup()
        self.radioBtnGroup.addButton(self.allRadioBtn)
        self.radioBtnGroup.addButton(self.allButLatestRadioBtn)
        self.radioBtnGroup.addButton(self.customRadioBtn)
        self.radioBtnGroup.buttonClicked.connect(self._checkBoxSwitch)
        
        
        self.rangeLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.rangeLayout)
        
        self.startLabel = QLabel("Start:")
        self.startLabel.setAlignment(Qt.AlignRight)
        self.rangeLayout.addWidget(self.startLabel)
        
        self.startNr = QSpinBox()
        self.startNr.setMinimum(1)
        self.startNr.setValue(1)
        self.startNr.setDisabled(True)
        self.rangeLayout.addWidget(self.startNr)
        
        self.endLabel = QLabel("End:")
        self.endLabel.setAlignment(Qt.AlignRight)
        self.rangeLayout.addWidget(self.endLabel)
        
        self.endNr = QSpinBox()
        self.endNr.setMinimum(2)
        self.endNr.setValue(2)
        self.endNr.setDisabled(True)
        self.rangeLayout.addWidget(self.endNr)
        
        self.startBtn = QPushButton("Start")
        self.startBtn.clicked.connect(self._startBtnClicked)
        self.mainLayout.addWidget(self.startBtn)
        
    def _startBtnClicked(self):
        if self.allRadioBtn.isChecked():
            self.signals.doAll.emit(self.TaskPath)
        elif self.allButLatestRadioBtn.isChecked():
            self.signals.doAllButLatest.emit(self.TaskPath)
        elif self.customRadioBtn.isChecked():
            self.signals.doCustom.emit(self.TaskPath, self.startNr.value(), self.endNr.value())
        
    def _checkBoxSwitch(self):
        if self.customRadioBtn.isChecked():
            self.startNr.setEnabled(True)
            self.endNr.setEnabled(True)
        else:
            self.startNr.setDisabled(True)
            self.endNr.setDisabled(True)
        
class Prism_Compression_Functions(object):
    programExts = []
    default = {"type":"Zip","zipLevel":"ZIP_DEFLATED","deleteOld":True}
    
    def __init__(self, core, plugin):
        self.core:PrismCore = core
        self.plugin = plugin
        self.icon = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "Resources", "Compression.png")
        
        self.popup = CompressingPopup()
        self.signals = pluginSignals()
        self.taskCompressionSignals = CompressionTaskSignals()

        # Signals for work thread
        self.signals.taskFinished.connect(self.popup.hide)
        self.signals.errorPopup.connect(self._errorPopup)
        self.signals.updateUI.connect(self._updateUI)
        self.signals.updateProgress.connect(self._updateProgressBar)
        
        # Signals for task popup
        self.taskCompressionSignals.doAll.connect(self._taskCompressAll)
        self.taskCompressionSignals.doAllButLatest.connect(self._taskCompressAllButLatest)
        self.taskCompressionSignals.doCustom.connect(self._taskCompressCustom)

        # On plugin loads to properly get the scene formats
        self.core.registerCallback("onPluginsLoaded", self._loadExts, plugin=self)
        
        # Right click callbacks in Prism UI
        self.core.registerCallback('openPBFileContextMenu', self.openPBFileContextMenu, plugin=self)
        self.core.registerCallback('openPBAssetTaskContextMenu', self.openPBAssetTaskContextMenu, plugin=self)
        
        # Project settings for handling plugin settings
        self.core.registerCallback("projectSettings_loadUI", self.projectSettings_loadUI, plugin=self)
        self.core.registerCallback("preProjectSettingsLoad", self.preProjectSettingsLoad, plugin=self.plugin)
        self.core.registerCallback("preProjectSettingsSave", self.preProjectSettingsSave, plugin=self.plugin)
        
        #self.core.registerCallback("",)
    
    def isActive(self):
        return True

    def _loadExts(self):
        self.programExts = self.core.getPluginSceneFormats()
        
        # Remove zip specific formats
        self.programExts.remove(".gz")
        self.programExts.remove(".zip")

    ### Functions for worker threads
    def _errorPopup(self, message:str):
        self.core.popup(message,"Compression Error")

    def _updateUI(self):
        self.core.pb.refreshUI()
        
    def _updateProgressBar(self, message:str):
        self.popup.label.setText(message)

    ### Functions for task popup
    
    def _getAllFiles(self, path:str) -> list:
        files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and f.endswith(tuple(self.programExts))]
        return files
    
    def _taskCompressAll(self, path:str):
        files = self._getAllFiles(path)
        self.doJob(filelist=files)
    
    def _taskCompressAllButLatest(self, path:str):
        files = self._getAllFiles(path)
        files.remove(files[-1])
        self.doJob(filelist=files)
    
    def _taskCompressCustom(self, path:str, start:int, end:int):
        files = self._getAllFiles(path)
        regex = r".*[vV](" + "|".join([f"{i:04d}" for i in range(start, end+1)]) + ").*"
        filteredFiles = []
        for f in files:
            if re.search(regex, f):
                filteredFiles.append(f)
        
        if len(filteredFiles) == 0:
            self.core.popup("No files found for the given range","Error")
            return
        
        self.doJob(filelist=filteredFiles)
        
    ###
    
    def getCompressionType(self):
        usePresets = self.core.getConfig("compression", "type", config="project")
        
        if usePresets == None:
            return self.default["type"]
        
        return usePresets
    
    def getDeleteOld(self):
        deleteOld = self.core.getConfig("compression", "deleteOld", config="project")
        
        if deleteOld == None:
            return self.default["deleteOld"]
        
        return deleteOld
    
    def getZipCompressionLevel(self):
        zipLevel = self.core.getConfig("compression", "zipLevel", config="project")
        
        if zipLevel == None:
            return self.default["zipLevel"]
        
        return zipLevel

    def customizeExecutable(self, origin, empty, force = None):
        if force is not None:
            self.doJob(force)
        return True

    def compressTask(self, path:str):
        self.popupTask = CompressionTask(self.taskCompressionSignals,path)
        self.popupTask.show()

    def doJob(self,path=None,filelist=None):
        compType = self.getCompressionType()
        deleteOld = self.getDeleteOld()
        CompressionLevel = CompressionZipType[self.getZipCompressionLevel()]
        
        self.worker = workerThread(self.signals, compType, deleteOld, CompressionLevel, filePath=path, fileList=filelist)
        self.popup.label.setText("Compressing files... Will close when completed.")
        self.popup.show()
        self.worker.start()

    def openPBAssetTaskContextMenu(self, *args):
        sceneBrowser:SceneBrowser.SceneBrowser = args[0]
        menu:QMenu = args[1]
        data = sceneBrowser.getSelectedContext()
        
        try:
            path = os.path.join(data['paths'][0], "Scenefiles", data['department'], data['task'])
        except:
            return
        
        if not os.path.exists(path):
            self.core.popup("Task folder does not exist","Error")
            return

        compressTask = QAction("Compress Task", menu)
        compressTask.triggered.connect(lambda: self.compressTask(path))
        compressTask.setIcon(QIcon(self.icon))
        menu.addAction(compressTask)

    def openPBFileContextMenu(self, *args):

        origin = args[0]
        menu:QMenu = args[1]
        data = args[2]
        
        if os.path.isfile(data) and (not data.endswith(".zip") and not data.endswith(".tar.gz")):
            CompressAction = QAction("Compress file", origin)
            CompressAction.triggered.connect(lambda: self.doJob(path=data))
            CompressAction.setIcon(QIcon(self.icon))
            menu.addAction(CompressAction)
        
        if os.path.isfile(data) and (data.endswith(".zip") or data.endswith(".tar.gz")):
            DecompressAction = QAction("Decompress file", origin)
            DecompressAction.triggered.connect(lambda: self.customizeExecutable(None,None,force=data))
            DecompressAction.setIcon(QIcon(self.icon))
            menu.addAction(DecompressAction)
    
    def projectSettings_loadUI(self, origin, *args):
        
        #TODO: add separators to force the compression settings to the center
        
        def changeVisibility():
            if origin.cmp_compTypeDropdown.currentText() == "Zip":
                zipCompressionLevel.setVisible(True)
                origin.cmp_zipCompressionLevel.setVisible(True)
            else:
                self.core.popup("Tar.gz is Experimental, Prism does not behave as intended. Use at your own risk","Warning")
                zipCompressionLevel.setVisible(False)
                origin.cmp_zipCompressionLevel.setVisible(False)
        
        # create a widget
        origin.w_myPlugin = QWidget()
        origin.lo_myPlugin = QVBoxLayout(origin.w_myPlugin)

        compTypeLayout = QHBoxLayout()
        origin.lo_myPlugin.addLayout(compTypeLayout)
        
        compression_type = QLabel("Compression type: ")
        compression_type.setAlignment(Qt.AlignRight)
        compTypeLayout.addWidget(compression_type)
        origin.cmp_compTypeDropdown = QComboBox()
        origin.cmp_compTypeDropdown.addItems(["Zip","Tar.gz"])
        origin.cmp_compTypeDropdown.setToolTip("Select the compression type to use")
        compTypeLayout.addWidget(origin.cmp_compTypeDropdown)

        # if origin.cmp_compTypeDropdown.currentText() == "Zip" show zip compression level
        origin.cmp_compTypeDropdown.currentTextChanged.connect(changeVisibility)

        zipCompressionLevelLayout = QHBoxLayout()
        origin.lo_myPlugin.addLayout(zipCompressionLevelLayout)
        
        zipCompressionLevel = QLabel("Zip Compression Level: ")
        zipCompressionLevel.setAlignment(Qt.AlignRight)
        zipCompressionLevel.setVisible(origin.cmp_compTypeDropdown.currentText() == "Zip")
        zipCompressionLevelLayout.addWidget(zipCompressionLevel)
        
        origin.cmp_zipCompressionLevel = QComboBox()
        origin.cmp_zipCompressionLevel.addItems(["ZIP_STORED",
                                                "ZIP_DEFLATED",
                                                "ZIP_BZIP2",
                                                "ZIP_LZMA"])
        origin.cmp_zipCompressionLevel.setToolTip("Select the compression level to use")
        origin.cmp_zipCompressionLevel.setVisible(origin.cmp_compTypeDropdown.currentText() == "Zip")
        origin.cmp_zipCompressionLevel.setCurrentText(self.default["zipLevel"])
        zipCompressionLevelLayout.addWidget(origin.cmp_zipCompressionLevel)

        deleteOldLayout = QHBoxLayout()
        origin.lo_myPlugin.addLayout(deleteOldLayout)
        
        deleteOld = QLabel("Delete old file after compression: ")
        deleteOld.setAlignment(Qt.AlignRight)
        deleteOldLayout.addWidget(deleteOld)
        
        origin.cmp_deleteOldCheckbox = QCheckBox()
        origin.cmp_deleteOldCheckbox.setToolTip("Delete the original file AFTER compression")
        deleteOldLayout.addWidget(origin.cmp_deleteOldCheckbox)

        origin.addTab(origin.w_myPlugin, "Compression")

    def preProjectSettingsLoad(self, origin, settings):
        if not settings:
            return
        
        if not "compression" in settings:
            settings["compression"] = {}
            settings["compression"]["type"] = "Zip"
            settings["compression"]["zipLevel"] = "ZIP_DEFLATED"
            settings["compression"]["deleteOld"] = True
            

        if "type" in settings["compression"]:
            origin.cmp_compTypeDropdown.setCurrentText(settings["compression"]["type"])
        
        if "zipLevel" in settings["compression"]:
            origin.cmp_zipCompressionLevel.setCurrentText(settings["compression"]["zipLevel"])
        
        if "deleteOld" in settings["compression"]:
            origin.cmp_deleteOldCheckbox.setChecked(settings["compression"]["deleteOld"])
            
    def preProjectSettingsSave(self, origin, settings):
        if "compression" not in settings:
            settings["compression"] = {}
            settings["compression"]["type"] = origin.cmp_compTypeDropdown.currentText()
            settings["compression"]["zipLevel"] = origin.cmp_zipCompressionLevel.currentText()
            settings["compression"]["deleteOld"] = origin.cmp_deleteOldCheckbox.isChecked()
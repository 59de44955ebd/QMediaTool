#****************************************************************************
# @file      QPyMediaTool - task manager
# @author    Valentin Schmidt
# @version   0.1
#****************************************************************************

import os

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic

from const import RES_DIR
from myprocess import MyProcess

class TaskManager(QWidget):

    statusMessage = pyqtSignal(str)
    outputMessage = pyqtSignal(str)
    outputClear = pyqtSignal()

    ########################################
    # @constructor
    ########################################
    def __init__ (self):
        super().__init__()
        uic.loadUi(RES_DIR + '/ui/taskmanager.ui', self)

        self._taskQueueRunning = False
        self._taskQueueStopOnError = False
        self._taskQueueCurrentIndex = 0

        self.listWidgetTaskQueue.setDragDropMode(QAbstractItemView.InternalMove)
        self.pushButtonTaskDelete.released.connect(self.slotTaskDelete)
        self.pushButtonTaskClear.released.connect(self.slotTaskClear)

        self.pushButtonRunTaskQueue.released.connect(self.slotRunTaskQueue)
        self.pushButtonStopTaskQueue.released.connect(self.slotStopTaskQueue)
        self.checkBoxTaskQueueStopOnError.clicked.connect(self.slotTaskQueueStopOnErrorClicked)

        self._proc = MyProcess()
        self._proc.readyReadStandardOutput.connect(self.slotStdout)
        self._proc.readyReadStandardError.connect(self.slotStderr)
        self._proc.finished.connect(self.slotComplete)

    ########################################
    #
    ########################################
    def quit (self):
        if self._proc.state() != QProcess.NotRunning:
            self._proc.kill()

    ########################################
    # Runs the next task in the task queue
    ########################################
    def runNextTask (self):
        if self._taskQueueCurrentIndex<self.listWidgetTaskQueue.count()-1:
            # get and run next task
            self._taskQueueCurrentIndex = self._taskQueueCurrentIndex + 1
            self.runTask(self.listWidgetTaskQueue.item(self._taskQueueCurrentIndex).data(Qt.UserRole))
        else:
            self.statusMessage.emit('TaskQueue finished')

    ########################################
    #
    ########################################
    def runTask (self, task):
        task.run(self._proc)
        self.statusMessage.emit('Task running...')

    ########################################
    #
    ########################################
    def addTask (self, task):
        taskItem = QListWidgetItem()
        taskItem.setText(task.name)
        taskItem.setData(Qt.UserRole, task)
        self.listWidgetTaskQueue.addItem(taskItem)
        self.pushButtonRunTaskQueue.setDisabled(False)

    ########################################
    #
    ########################################
    def updateUI (self, running):
        # change button activation
        self.pushButtonRunTaskQueue.setDisabled(running)
        self.pushButtonStopTaskQueue.setDisabled(not running)

        # deactivate task queue widgets
        self.listWidgetTaskQueue.setDisabled(running)

        self.pushButtonTaskAdd.setDisabled(running)
        self.pushButtonTaskDelete.setDisabled(running)
        self.pushButtonTaskClear.setDisabled(running)

    ########################################
    # @callback
    ########################################
    def slotTaskDelete(self):
        # @todo: check if queue is running
        row = self.listWidgetTaskQueue.currentRow()
        if row>=0:
            self.listWidgetTaskQueue.takeItem(row)
            if self.listWidgetTaskQueue.count() == 0:
                self.pushButtonRunTaskQueue.setDisabled(True)

    ########################################
    # @callback
    ########################################
    def slotTaskClear (self):
        # @todo: check if queue is running
        self.listWidgetTaskQueue.clear()
        self.pushButtonRunTaskQueue.setDisabled(True)

    ########################################
    # @callback
    ########################################
    def slotRunTaskQueue (self):
        self.statusMessage.emit('')
        self.outputClear.emit()  # ???
        self._taskQueueFailures = 0
        self._taskQueueRunning = True
        self.updateUI(True)

        # get and run first task in queue
        self._taskQueueCurrentIndex = 0
        self.runTask(self.listWidgetTaskQueue.item(0).data(Qt.UserRole))

    ########################################
    # @callback
    ########################################
    def slotStopTaskQueue (self):
        self._taskQueueRunning = False
        if self._proc.state() != QProcess.NotRunning:
            self._proc.kill()
        self.updateUI(False)
        self.outputMessage.emit('\nTask Queue was stopped by User.')

    ########################################
    # @callback
    ########################################
    def slotTaskQueueStopOnErrorClicked (self, checked):
        self._taskQueueStopOnError = checked

    ########################################
    # @callback
    ########################################
    def slotTaskQueueFinished (self):
        msg = 'Task Queue Finished (' + str(self._taskQueueFailures) + ' Tasks failed)'
        self.statusMessage.emit(msg)
        self.outputMessage.emit(msg)
        self.updateUI(False)

    ########################################
    # @callback
    ########################################
    def slotStdout (self):
        s = self._proc.readAllStandardOutput().data().decode()
        self.outputMessage.emit(s)

    ########################################
    # @callback
    ########################################
    def slotStderr (self):
        s = self._proc.readAllStandardError().data().decode()
        self.outputMessage.emit(s)

    ########################################
    # @callback
    ########################################
    def slotComplete (self, exitCode, exitStatus):

        # update task item color according to success state
        taskItem = self.listWidgetTaskQueue.item(self._taskQueueCurrentIndex)
        if exitCode == 0:
            taskItem.setBackground(QColor(0, 127, 0))
        else:
            taskItem.setBackground(QColor(127, 0, 0))
            self._taskQueueFailures += 1
        if self._taskQueueCurrentIndex<self.listWidgetTaskQueue.count() - 1:
            if exitCode == 0 or not self._taskQueueStopOnError:
                self.runNextTask()
            else:
                self.slotTaskQueueFinished()
        else:
            self.slotTaskQueueFinished()

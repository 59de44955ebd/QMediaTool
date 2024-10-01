"""
QMediaTool - task manager
"""

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
    #
    ########################################
    def __init__ (self):
        super().__init__()
        uic.loadUi(os.path.join(RES_DIR, 'ui', 'taskmanager.ui'), self)

        self._taskQueueRunning = False
        self._taskQueueStopOnError = False
        self._taskQueueCurrentIndex = 0

        self.listWidgetTaskQueue.setDragDropMode(QAbstractItemView.InternalMove)
        self.pushButtonTaskDelete.released.connect(self.slot_task_delete)
        self.pushButtonTaskClear.released.connect(self.slot_task_clear)

        self.pushButtonRunTaskQueue.released.connect(self.slot_run_task_queue)
        self.pushButtonStopTaskQueue.released.connect(self.slot_stop_task_queue)
        self.checkBoxTaskQueueStopOnError.clicked.connect(self.slot_task_queue_stop_on_error_clicked)

        self._proc = MyProcess()
        self._proc.readyReadStandardOutput.connect(self.slot_stdout)
        self._proc.readyReadStandardError.connect(self.slot_stderr)
        self._proc.finished.connect(self.slot_complete)

    ########################################
    #
    ########################################
    def quit (self):
        if self._proc.state() != QProcess.NotRunning:
            self._proc.kill()

    ########################################
    # Runs the next task in the task queue
    ########################################
    def run_next_task (self):
        if self._taskQueueCurrentIndex < self.listWidgetTaskQueue.count() - 1:
            # get and run next task
            self._taskQueueCurrentIndex = self._taskQueueCurrentIndex + 1
            self.run_task(self.listWidgetTaskQueue.item(self._taskQueueCurrentIndex).data(Qt.UserRole))
        else:
            self.statusMessage.emit('TaskQueue finished')

    ########################################
    #
    ########################################
    def run_task (self, task):
        task.run(self._proc)
        self.statusMessage.emit('Task running...')

    ########################################
    #
    ########################################
    def add_task (self, task):
        taskItem = QListWidgetItem()
        taskItem.setText(task.name)
        taskItem.setData(Qt.UserRole, task)
        self.listWidgetTaskQueue.addItem(taskItem)
        self.pushButtonRunTaskQueue.setDisabled(False)

    ########################################
    #
    ########################################
    def update_ui (self, running):
        # change button activation
        self.pushButtonRunTaskQueue.setDisabled(running)
        self.pushButtonStopTaskQueue.setDisabled(not running)

        # deactivate task queue widgets
        self.listWidgetTaskQueue.setDisabled(running)

        self.pushButtonTaskAdd.setDisabled(running)
        self.pushButtonTaskDelete.setDisabled(running)
        self.pushButtonTaskClear.setDisabled(running)

    ########################################
    #
    ########################################
    def slot_task_delete(self):
        # @todo: check if queue is running
        row = self.listWidgetTaskQueue.currentRow()
        if row >= 0:
            self.listWidgetTaskQueue.takeItem(row)
            if self.listWidgetTaskQueue.count() == 0:
                self.pushButtonRunTaskQueue.setDisabled(True)

    ########################################
    #
    ########################################
    def slot_task_clear (self):
        # @todo: check if queue is running
        self.listWidgetTaskQueue.clear()
        self.pushButtonRunTaskQueue.setDisabled(True)

    ########################################
    #
    ########################################
    def slot_run_task_queue (self):
        self.statusMessage.emit('')
        self.outputClear.emit()  # ???
        self._taskQueueFailures = 0
        self._taskQueueRunning = True
        self.update_ui(True)

        # get and run first task in queue
        self._taskQueueCurrentIndex = 0
        self.run_task(self.listWidgetTaskQueue.item(0).data(Qt.UserRole))

    ########################################
    #
    ########################################
    def slot_stop_task_queue (self):
        self._taskQueueRunning = False
        if self._proc.state() != QProcess.NotRunning:
            self._proc.kill()
        self.update_ui(False)
        self.outputMessage.emit('\nTask Queue was stopped by User.')

    ########################################
    #
    ########################################
    def slot_task_queue_stop_on_error_clicked (self, checked):
        self._taskQueueStopOnError = checked

    ########################################
    #
    ########################################
    def slot_task_queue_finished (self):
        msg = f'Task Queue Finished ({self._taskQueueFailures} Tasks failed)'
        self.statusMessage.emit(msg)
        self.outputMessage.emit(msg)
        self.update_ui(False)

    ########################################
    #
    ########################################
    def slot_stdout (self):
        s = self._proc.readAllStandardOutput().data().decode()
        self.outputMessage.emit(s)

    ########################################
    #
    ########################################
    def slot_stderr (self):
        s = self._proc.readAllStandardError().data().decode()
        self.outputMessage.emit(s)

    ########################################
    #
    ########################################
    def slot_complete (self, exitCode, exitStatus):
        # update task item color according to success state
        taskItem = self.listWidgetTaskQueue.item(self._taskQueueCurrentIndex)
        if exitCode == 0:
            taskItem.setBackground(QColor('#007F00'))
        else:
            taskItem.setBackground(QColor('#7F0000'))
            self._taskQueueFailures += 1
        if self._taskQueueCurrentIndex<self.listWidgetTaskQueue.count() - 1:
            if exitCode == 0 or not self._taskQueueStopOnError:
                self.run_next_task()
            else:
                self.slot_task_queue_finished()
        else:
            self.slot_task_queue_finished()

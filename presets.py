"""
QMediaTool - presets manager
"""

import sqlite3

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5 import uic

from const import *


class PresetsManager(QDialog):

	presetChanged = pyqtSignal(int)
	message = pyqtSignal(str)
	error = pyqtSignal(str)

	########################################--
	#
	########################################--
	def __init__(self, parent, presets_db):
		super().__init__(parent)
		self._presets_db = presets_db

		uic.loadUi(os.path.join(RES_DIR, 'ui', 'presets.ui'), self)
		self.lineEditPresetName.textEdited.connect(self.slot_check_complete)
		self.plainTextEditCommandLine.textChanged.connect(self.slot_check_complete)
		self.pushButtonSave.released.connect(self.slot_save)
		self.pushButtonSaveAsNew.released.connect(self.slot_save_as_new)
		self.pushButtonCancel.released.connect(self.close)
		self._presets_id = None

	########################################
	#
	########################################
	def show (self, presets_id=None, catID=None):
		self.comboBoxCategories.clear()
		c = self._presets_db.cursor()
		sql = "SELECT * FROM categories ORDER BY name"
		c.execute(sql)
		for row in c.fetchall():
			self.comboBoxCategories.addItem(row['name'], row['id'])
		self._set_preset(presets_id)
		if presets_id is None:
			self.setWindowTitle('New Preset')
			self._set_category(catID)
		else:
			self.setWindowTitle('Edit Preset')
		super().show()

	########################################
	#
	########################################
	def _set_preset (self, presets_id=None):
		self._presets_id = presets_id
		if presets_id:
			c = self._presets_db.cursor()
			sql = """
			SELECT presets.*,categories.name AS category FROM presets
			LEFT JOIN categories ON presets.category_id=categories.id WHERE presets.id=?
			"""
			c.execute(sql, (presets_id,))
			preset = c.fetchone()
			if preset is None:
			    return
			self.lineEditPresetName.setText(preset['name'])
			self.plainTextEditNotes.setPlainText(preset['notes'])
			self.plainTextEditCommandLine.setPlainText(preset['cmd'])
			if preset['input_type'] == INPUT_TYPE_FILES:
				self.radioButtonMultiple.setChecked(True)
			elif preset['input_type'] == INPUT_TYPE_URL:
				self.radioButtonURL.setChecked(True)
			elif preset['input_type'] == INPUT_TYPE_NONE:
				self.radioButtonNone.setChecked(True)
			else:
				self.radioButtonSingle.setChecked(True)
			ext = preset['ext']
			self.lineEditExtensions.setText(ext)
			index = self.comboBoxCategories.findData(preset['category_id'])
			self.comboBoxCategories.setCurrentIndex(index)
		else:
			self.lineEditPresetName.setText('')
			self.plainTextEditNotes.setPlainText('')
			self.plainTextEditCommandLine.setPlainText('')
			self.radioButtonSingle.setChecked(True)
			self.lineEditExtensions.setText('')
			self.pushButtonSave.setDisabled(True)
			self.pushButtonSaveAsNew.setDisabled(True)

	########################################
	#
	########################################
	def _set_category (self, catID=None):
		if catID:
			index = self.comboBoxCategories.findData(catID)
			self.comboBoxCategories.setCurrentIndex(index)
		else:
			self.comboBoxCategories.setCurrentIndex(0)

	########################################
	#
	########################################
	def slot_save (self):
		catID = self.comboBoxCategories.currentData()
		name = self.lineEditPresetName.text()
		notes = self.plainTextEditNotes.toPlainText()
		cmd = self.plainTextEditCommandLine.toPlainText()
		ext = self.lineEditExtensions.text()
		if self.radioButtonMultiple.isChecked():
			input_type = INPUT_TYPE_FILES
		elif self.radioButtonURL.isChecked():
			input_type = INPUT_TYPE_URL
		elif self.radioButtonNone.isChecked():
			input_type = INPUT_TYPE_NONE
		else:
			input_type = INPUT_TYPE_FILE
		try:
			c = self._presets_db.cursor()
			sql = "UPDATE presets SET category_id=?, name=?, notes=?, cmd=?, ext=?, input_type=? WHERE id=?"
			c.execute(sql, (catID,name,notes,cmd,ext,input_type, self._presets_id))
			self._presets_db.commit()
			self.presetChanged.emit(self._presets_id)
			self.message.emit('Changes successfully saved')
			self.close()
		except sqlite3.Error as e:
			self.error.emit(e.args[0])

	########################################
	#
	########################################
	def slot_save_as_new (self):
		catID = self.comboBoxCategories.currentData()
		name = self.lineEditPresetName.text()
		notes = self.plainTextEditNotes.toPlainText()
		cmd = self.plainTextEditCommandLine.toPlainText()
		ext = self.lineEditExtensions.text()
		if self.radioButtonMultiple.isChecked():
			input_type = INPUT_TYPE_FILES
		elif self.radioButtonURL.isChecked():
			input_type = INPUT_TYPE_URL
		elif self.radioButtonNone.isChecked():
			input_type = INPUT_TYPE_NONE
		else:
			input_type = INPUT_TYPE_FILE
		try:
			c = self._presets_db.cursor()
			sql = "INSERT INTO presets(category_id, name, notes, cmd, ext, input_type) VALUES(?,?,?,?,?,?)"
			c.execute(sql, (catID, name, notes, cmd, ext, input_type))
			self._presets_db.commit()
			self.presetChanged.emit(c.lastrowid)
			self.message.emit('Changes successfully saved')
			self.close()
		except sqlite3.Error as e:
			self.error.emit(e.args[0])

	########################################
	#
	########################################
	def slot_check_complete(self):
		is_complete = self.lineEditPresetName.text() != '' and self.plainTextEditCommandLine.toPlainText() != ''
		if self._presets_id is not None:
			self.pushButtonSave.setDisabled(not is_complete)
		self.pushButtonSaveAsNew.setDisabled(not is_complete)

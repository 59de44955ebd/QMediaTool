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

	########################################--
	# @constructor
	########################################--
	def __init__(self, parent):
		super().__init__(parent)
		self._main = parent
		uic.loadUi(RES_DIR + '/ui/presets.ui', self)

		self.lineEditPresetName.textEdited.connect(self.slotCheckComplete)
		self.plainTextEditCommandLine.textChanged.connect(self.slotCheckComplete)
		self.pushButtonSave.released.connect(self.slotSave)
		self.pushButtonSaveAsNew.released.connect(self.slotSaveAsNew)
		self.pushButtonCancel.released.connect(self.close)

		self._presetID = None

	########################################
	#
	########################################
	def show (self, presetID=None, catID=None):
		self.comboBoxCategories.clear()
		c = self._main._presetsDB.cursor()
		sql = "SELECT * FROM categories ORDER BY name"
		c.execute(sql)
		for row in c.fetchall():
			self.comboBoxCategories.addItem(row['name'], row['id'])
		self._setPreset(presetID)

		if presetID is None:
			self.setWindowTitle('New Preset')
			self._setCategory(catID)
		else:
			self.setWindowTitle('Edit Preset')

		super().show()

	########################################
	#
	########################################
	def _setPreset (self, presetID=None):
		self._presetID = presetID
		if presetID:
			c = self._main._presetsDB.cursor()
			sql = """
			SELECT presets.*,categories.name AS category FROM presets
			LEFT JOIN categories ON presets.category_id=categories.id WHERE presets.id=?
			"""
			c.execute(sql, (presetID,))
			preset = c.fetchone()
			if preset is None: return

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
			self.plainTextEditCommandLine.setPlainText('')
			self.radioButtonSingle.setChecked(True)
			self.lineEditExtensions.setText('')

			self.pushButtonSave.setDisabled(True)
			self.pushButtonSaveAsNew.setDisabled(True)

	########################################
	#
	########################################
	def _setCategory (self, catID=None):
		if catID:
			index = self.comboBoxCategories.findData(catID)
			self.comboBoxCategories.setCurrentIndex(index)
		else:
			self.comboBoxCategories.setCurrentIndex(0)

	########################################
	# @callback
	########################################
	def slotSave (self):
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
			c = self._main._presetsDB.cursor()
			sql = "UPDATE presets SET category_id=?, name=?, notes=?, cmd=?, ext=?, input_type=? WHERE id=?"
			c.execute(sql, (catID,name,notes,cmd,ext,input_type, self._presetID))
			self._main._presetsDB.commit()

			self.presetChanged.emit(self._presetID)

			self._main.msg('Changes successfully saved')
			self.close()

		except sqlite3.Error as e:
			self._main.err(e.args[0])

	########################################
	# @callback
	########################################
	def slotSaveAsNew (self):
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
			c = self._main._presetsDB.cursor()
			sql = "INSERT INTO presets(category_id, name, notes, cmd, ext, input_type) VALUES(?,?,?,?,?,?)"
			c.execute(sql, (catID, name, notes, cmd, ext, input_type))
			self._main._presetsDB.commit()

			self.presetChanged.emit(c.lastrowid)

			self._main.msg('Changes successfully saved')
			self.close()

		except sqlite3.Error as e:
			self._main.err(e.args[0])

	########################################
	# @callback
	########################################
	def slotCheckComplete (self):
		is_complete = self.lineEditPresetName.text() != '' and self.plainTextEditCommandLine.toPlainText() != ''
		if self._presetID is not None:
			self.pushButtonSave.setDisabled(not is_complete)
		self.pushButtonSaveAsNew.setDisabled(not is_complete)

from PyQt6 import QtWidgets
from src.ui.app import OscilloscopeApp

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = OscilloscopeApp()
    window.show()
    app.exec()

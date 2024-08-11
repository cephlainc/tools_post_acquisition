import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFileDialog
from PyQt5.QtCore import Qt

from script_visualization import run_visualization, load_acquisition_parameters

class VisualizationGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Folder selection
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        folder_button = QPushButton("Select Folder")
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(QLabel("Image Folder:"))
        folder_layout.addWidget(self.folder_edit)
        folder_layout.addWidget(folder_button)
        layout.addLayout(folder_layout)

        # XY Binning
        xy_binning_layout = QHBoxLayout()
        self.xy_binning_edit = QLineEdit()
        xy_binning_layout.addWidget(QLabel("XY Binning:"))
        xy_binning_layout.addWidget(self.xy_binning_edit)
        layout.addLayout(xy_binning_layout)

        # Z Downsample
        z_downsample_layout = QHBoxLayout()
        self.z_downsample_edit = QLineEdit()
        z_downsample_layout.addWidget(QLabel("Z Downsample Factor:"))
        z_downsample_layout.addWidget(self.z_downsample_edit)
        layout.addLayout(z_downsample_layout)

        # Z Range
        z_range_layout = QHBoxLayout()
        self.z_start_edit = QLineEdit()
        self.z_end_edit = QLineEdit()
        z_range_layout.addWidget(QLabel("Z Range:"))
        z_range_layout.addWidget(self.z_start_edit)
        z_range_layout.addWidget(QLabel("to"))
        z_range_layout.addWidget(self.z_end_edit)
        layout.addLayout(z_range_layout)

        # Crop Size
        crop_size_layout = QHBoxLayout()
        self.crop_size_edit = QLineEdit()
        crop_size_layout.addWidget(QLabel("Crop Size (optional):"))
        crop_size_layout.addWidget(self.crop_size_edit)
        layout.addLayout(crop_size_layout)

        # Acquisition Parameters Display
        self.params_label = QLabel("Acquisition Parameters: Not loaded")
        layout.addWidget(self.params_label)

        # Visualize button
        visualize_button = QPushButton("Visualize")
        visualize_button.clicked.connect(self.run_visualization)
        layout.addWidget(visualize_button)

        self.setLayout(layout)
        self.setWindowTitle('3D Visualization Parameters')
        self.show()

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.folder_edit.setText(folder)
        self.update_acquisition_params(folder)

    def update_acquisition_params(self, folder):
        try:
            params = load_acquisition_parameters(folder)
            self.params_label.setText(f"Acquisition Parameters: Z-step: {params['dz(um)']:.2f} µm, "
                                      f"Pixel size: {params['sensor_pixel_size_um']} µm, "
                                      f"Magnification: {params['objective']['magnification']}x")
        except Exception as e:
            self.params_label.setText(f"Error loading acquisition parameters: {str(e)}")

    def run_visualization(self):
        folder_path = self.folder_edit.text()
        xy_binning = int(self.xy_binning_edit.text()) if self.xy_binning_edit.text() else 1
        z_downsample = int(self.z_downsample_edit.text()) if self.z_downsample_edit.text() else 1
        z_start = int(self.z_start_edit.text()) if self.z_start_edit.text() else None
        z_end = int(self.z_end_edit.text()) if self.z_end_edit.text() else None
        z_range = (z_start, z_end) if z_start is not None and z_end is not None else None
        crop_size = int(self.crop_size_edit.text()) if self.crop_size_edit.text() else None

        run_visualization(folder_path, xy_binning, z_downsample, z_range, crop_size)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = VisualizationGUI()
    sys.exit(app.exec_())

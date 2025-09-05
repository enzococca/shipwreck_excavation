# -*- coding: utf-8 -*-
"""
3D Model Viewer Widget for OBJ files
"""

import os
import sys
from qgis.PyQt.QtCore import Qt, QUrl, pyqtSignal
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                                QLabel, QFileDialog, QMessageBox, QSlider,
                                QCheckBox, QGroupBox, QToolBar, QAction)
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsMessageLog, Qgis

# Try to import Qt3D for 3D rendering
try:
    from PyQt5.Qt3DCore import QEntity, QTransform
    from PyQt5.Qt3DRender import (QCamera, QCameraLens, QClearBuffers, QMesh,
                                  QPhongMaterial, QDirectionalLight, QTexture2D,
                                  QTextureImage, QDiffuseMapMaterial)
    from PyQt5.Qt3DExtras import Qt3DWindow, QForwardRenderer, QOrbitCameraController
    from PyQt5.QtWidgets import QWidget as Qt3DWidget
    QT3D_AVAILABLE = True
except ImportError:
    QT3D_AVAILABLE = False

# Fallback to VTK if available
try:
    import vtk
    from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    VTK_AVAILABLE = True
except ImportError:
    VTK_AVAILABLE = False


class ModelViewerWidget(QWidget):
    """Widget for viewing 3D models (OBJ files with textures)"""
    
    model_loaded = pyqtSignal(str)  # Emitted when a model is loaded
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_model_path = None
        self.current_texture_path = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar = QToolBar()
        
        # Load model action
        load_action = QAction(QIcon(), self.tr("Load Model"), self)
        load_action.triggered.connect(self.load_model)
        toolbar.addAction(load_action)
        
        # Load texture action
        texture_action = QAction(QIcon(), self.tr("Load Texture"), self)
        texture_action.triggered.connect(self.load_texture)
        toolbar.addAction(texture_action)
        
        toolbar.addSeparator()
        
        # Reset view action
        reset_action = QAction(QIcon(), self.tr("Reset View"), self)
        reset_action.triggered.connect(self.reset_view)
        toolbar.addAction(reset_action)
        
        # Screenshot action
        screenshot_action = QAction(QIcon(), self.tr("Screenshot"), self)
        screenshot_action.triggered.connect(self.take_screenshot)
        toolbar.addAction(screenshot_action)
        
        layout.addWidget(toolbar)
        
        # 3D viewer area
        if QT3D_AVAILABLE:
            self.viewer = self.create_qt3d_viewer()
            self.viewer_type = "Qt3D"
        elif VTK_AVAILABLE:
            self.viewer = self.create_vtk_viewer()
            self.viewer_type = "VTK"
        else:
            # Fallback to image preview
            self.viewer = QLabel(self.tr("3D viewer not available.\nInstall PyQt3D or VTK for 3D model viewing."))
            self.viewer.setAlignment(Qt.AlignCenter)
            self.viewer.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc;")
            self.viewer_type = "None"
        
        layout.addWidget(self.viewer, 1)
        
        # Controls
        controls_group = QGroupBox(self.tr("Controls"))
        controls_layout = QVBoxLayout()
        
        # Lighting control
        lighting_layout = QHBoxLayout()
        lighting_layout.addWidget(QLabel(self.tr("Lighting:")))
        self.lighting_slider = QSlider(Qt.Horizontal)
        self.lighting_slider.setRange(0, 100)
        self.lighting_slider.setValue(50)
        self.lighting_slider.valueChanged.connect(self.update_lighting)
        lighting_layout.addWidget(self.lighting_slider)
        controls_layout.addLayout(lighting_layout)
        
        # Wireframe option
        self.wireframe_check = QCheckBox(self.tr("Show Wireframe"))
        self.wireframe_check.toggled.connect(self.toggle_wireframe)
        controls_layout.addWidget(self.wireframe_check)
        
        # Texture option
        self.texture_check = QCheckBox(self.tr("Show Texture"))
        self.texture_check.setChecked(True)
        self.texture_check.toggled.connect(self.toggle_texture)
        controls_layout.addWidget(self.texture_check)
        
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        # Info panel
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        self.setLayout(layout)
        
    def create_qt3d_viewer(self):
        """Create Qt3D viewer"""
        if not QT3D_AVAILABLE:
            return None
            
        # Create 3D window
        view_3d = Qt3DWindow()
        view_3d.defaultFrameGraph().setClearColor(Qt.lightGray)
        
        # Camera
        camera = view_3d.camera()
        camera.setProjectionType(QCameraLens.PerspectiveProjection)
        camera.setFieldOfView(45)
        camera.setNearPlane(0.1)
        camera.setFarPlane(1000.0)
        camera.setPosition(QVector3D(0, 0, 40))
        camera.setViewCenter(QVector3D(0, 0, 0))
        
        # Scene
        self.root_entity = QEntity()
        
        # Light
        light_entity = QEntity(self.root_entity)
        self.light = QDirectionalLight()
        self.light.setWorldDirection(QVector3D(1, -1, -1))
        light_entity.addComponent(self.light)
        
        # Camera controller
        cam_controller = QOrbitCameraController(self.root_entity)
        cam_controller.setCamera(camera)
        
        view_3d.setRootEntity(self.root_entity)
        
        # Embed in widget
        container = QWidget.createWindowContainer(view_3d)
        return container
        
    def create_vtk_viewer(self):
        """Create VTK viewer"""
        if not VTK_AVAILABLE:
            return None
            
        # Create VTK widget
        vtk_widget = QVTKRenderWindowInteractor()
        
        # Create renderer
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.9, 0.9, 0.9)
        
        # Add renderer to widget
        vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        
        # Create interactor style
        style = vtk.vtkInteractorStyleTrackballCamera()
        vtk_widget.SetInteractorStyle(style)
        
        # Add axes
        axes = vtk.vtkAxesActor()
        self.renderer.AddActor(axes)
        
        # Add light
        self.light = vtk.vtkLight()
        self.light.SetPosition(1, 1, 1)
        self.renderer.AddLight(self.light)
        
        return vtk_widget
        
    def load_model(self, file_path=None):
        """Load OBJ model file"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Load 3D Model"),
                "",
                "OBJ Files (*.obj);;All Files (*.*)"
            )
            
        if not file_path:
            return
            
        self.current_model_path = file_path
        
        # Look for associated MTL and texture files
        base_name = os.path.splitext(file_path)[0]
        mtl_path = base_name + '.mtl'
        
        # Check for textures
        texture_extensions = ['.jpg', '.jpeg', '.png', '.tga', '.bmp']
        texture_found = False
        
        # First check for texture with same base name
        for ext in texture_extensions:
            texture_path = base_name + ext
            if os.path.exists(texture_path):
                self.current_texture_path = texture_path
                texture_found = True
                break
        
        # If MTL exists, parse it for texture references
        if not texture_found and os.path.exists(mtl_path):
            try:
                with open(mtl_path, 'r') as f:
                    mtl_content = f.read()
                import re
                # Look for texture references in MTL
                texture_patterns = [
                    r'map_Kd\s+(.+)',  # Diffuse texture
                    r'map_Ka\s+(.+)',  # Ambient texture
                ]
                for pattern in texture_patterns:
                    matches = re.findall(pattern, mtl_content)
                    if matches:
                        texture_file = matches[0].strip()
                        # Try absolute and relative paths
                        texture_full_path = os.path.join(os.path.dirname(file_path), texture_file)
                        if os.path.exists(texture_full_path):
                            self.current_texture_path = texture_full_path
                            texture_found = True
                            break
            except Exception as e:
                print(f"Error parsing MTL: {e}")
        
        # Update info
        file_info = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
        info_text = self.tr(f"Model: {file_info}\nSize: {file_size:.2f} MB")
        
        if os.path.exists(mtl_path):
            info_text += self.tr("\nMTL file found")
        if texture_found:
            info_text += self.tr(f"\nTexture: {os.path.basename(self.current_texture_path)}")
        else:
            info_text += self.tr("\nNo texture found")
            
        self.info_label.setText(info_text)
        
        # Debug log
        from qgis.core import QgsMessageLog
        QgsMessageLog.logMessage(f"Model: {file_path}", "Shipwreck", level=0)
        QgsMessageLog.logMessage(f"MTL exists: {os.path.exists(mtl_path)}", "Shipwreck", level=0)
        QgsMessageLog.logMessage(f"Texture found: {texture_found}", "Shipwreck", level=0)
        if texture_found:
            QgsMessageLog.logMessage(f"Texture path: {self.current_texture_path}", "Shipwreck", level=0)
        
        # Load model based on viewer type
        if self.viewer_type == "Qt3D":
            self.load_model_qt3d(file_path)
        elif self.viewer_type == "VTK":
            self.load_model_vtk(file_path)
        else:
            # Show preview image if available
            preview_path = file_path.replace('.obj', '_preview.png')
            if os.path.exists(preview_path):
                pixmap = QPixmap(preview_path)
                self.viewer.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio))
                
        self.model_loaded.emit(file_path)
        
    def load_model_qt3d(self, file_path):
        """Load model using Qt3D"""
        if not QT3D_AVAILABLE:
            return
            
        # Remove existing model
        for child in self.root_entity.children():
            if isinstance(child, QEntity) and child != self.light.parent():
                child.deleteLater()
                
        # Create model entity
        model_entity = QEntity(self.root_entity)
        
        # Load mesh
        mesh = QMesh()
        mesh.setSource(QUrl.fromLocalFile(file_path))
        
        # Create material
        if self.current_texture_path and os.path.exists(self.current_texture_path):
            material = QDiffuseMapMaterial()
            texture = QTexture2D()
            texture_image = QTextureImage()
            texture_image.setSource(QUrl.fromLocalFile(self.current_texture_path))
            texture.addTextureImage(texture_image)
            material.setDiffuse(texture)
        else:
            material = QPhongMaterial()
            material.setDiffuse(Qt.gray)
            
        # Add components
        model_entity.addComponent(mesh)
        model_entity.addComponent(material)
        
    def load_model_vtk(self, file_path):
        """Load model using VTK"""
        if not VTK_AVAILABLE:
            return
            
        # Clear existing actors
        self.renderer.RemoveAllViewProps()
        
        # Read OBJ file
        reader = vtk.vtkOBJReader()
        reader.SetFileName(file_path)
        reader.Update()
        
        # Create mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        
        # Create actor
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(mapper)
        
        # Apply texture if available
        if self.current_texture_path and os.path.exists(self.current_texture_path):
            # Determine texture reader based on file extension
            texture_ext = os.path.splitext(self.current_texture_path)[1].lower()
            
            if texture_ext in ['.jpg', '.jpeg']:
                texture_reader = vtk.vtkJPEGReader()
            elif texture_ext == '.png':
                texture_reader = vtk.vtkPNGReader()
            elif texture_ext == '.bmp':
                texture_reader = vtk.vtkBMPReader()
            elif texture_ext == '.tga':
                texture_reader = vtk.vtkTGAReader()
            else:
                # Try PNG reader as default
                texture_reader = vtk.vtkPNGReader()
                
            texture_reader.SetFileName(self.current_texture_path)
            
            # Create texture
            texture = vtk.vtkTexture()
            texture.SetInputConnection(texture_reader.GetOutputPort())
            
            self.actor.SetTexture(texture)
            
            QgsMessageLog.logMessage(f"Texture applied: {self.current_texture_path}", "Shipwreck", level=0)
            
        # Add actor to renderer
        self.renderer.AddActor(self.actor)
        
        # Reset camera
        self.renderer.ResetCamera()
        self.viewer.GetRenderWindow().Render()
        
    def load_texture(self, file_path=None):
        """Load texture file"""
        if not file_path:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                self.tr("Load Texture"),
                "",
                "Image Files (*.png *.jpg *.jpeg *.bmp);;All Files (*.*)"
            )
            
        if not file_path:
            return
            
        self.current_texture_path = file_path
        
        # Reload model with new texture
        if self.current_model_path:
            self.load_model(self.current_model_path)
            
    def reset_view(self):
        """Reset camera view"""
        if self.viewer_type == "VTK" and hasattr(self, 'renderer'):
            self.renderer.ResetCamera()
            self.viewer.GetRenderWindow().Render()
            
    def take_screenshot(self):
        """Take screenshot of 3D view"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save Screenshot"),
            "screenshot.png",
            "PNG Files (*.png);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        if self.viewer_type == "VTK":
            # VTK screenshot
            window_to_image = vtk.vtkWindowToImageFilter()
            window_to_image.SetInput(self.viewer.GetRenderWindow())
            window_to_image.Update()
            
            writer = vtk.vtkPNGWriter()
            writer.SetFileName(file_path)
            writer.SetInputConnection(window_to_image.GetOutputPort())
            writer.Write()
            
            QMessageBox.information(
                self,
                self.tr("Success"),
                self.tr("Screenshot saved successfully")
            )
            
    def update_lighting(self, value):
        """Update lighting intensity"""
        intensity = value / 100.0
        
        if self.viewer_type == "VTK" and hasattr(self, 'light'):
            self.light.SetIntensity(intensity)
            self.viewer.GetRenderWindow().Render()
            
    def toggle_wireframe(self, checked):
        """Toggle wireframe display"""
        if self.viewer_type == "VTK" and hasattr(self, 'actor'):
            if checked:
                self.actor.GetProperty().SetRepresentationToWireframe()
            else:
                self.actor.GetProperty().SetRepresentationToSurface()
            self.viewer.GetRenderWindow().Render()
            
    def toggle_texture(self, checked):
        """Toggle texture display"""
        if self.current_model_path:
            self.load_model(self.current_model_path)
            
    def tr(self, message):
        """Translate message"""
        from qgis.PyQt.QtCore import QCoreApplication
        return QCoreApplication.translate('ModelViewerWidget', message)
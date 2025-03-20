import sys
import math
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QGraphicsScene, QGraphicsView, QGraphicsPixmapItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem,
    QGraphicsItem, QShortcut, QInputDialog, QUndoStack, QUndoCommand,
    QListWidget, QLabel, QDialog, QFormLayout, QLineEdit, QCheckBox,
    QDialogButtonBox, QAbstractItemView, QPlainTextEdit
)
from PyQt5.QtGui import (
    QPixmap, QIcon, QPen, QBrush, QPainter, QKeySequence, QTransform
)
from PyQt5.QtCore import Qt, QRectF, QPointF

##############################################################################
#                        Component Property Definitions                      #
##############################################################################
COMPONENT_PROPERTIES = {
    "BS": {  # new beam splitter
        "name": {"label": "Name", "required": True, "default": "", "type": "str"},
        "R": {"label": "Reflectivity", "required": False, "default": "", "type": "float"},
        "T": {"label": "Transmissivity", "required": False, "default": "", "type": "float"},
        "L": {"label": "Loss", "required": False, "default": "", "type": "float"},
        "phi": {"label": "Microscopic tuning (°)", "required": False, "default": "", "type": "float"},
        "alpha": {"label": "Angle of incidence (°)", "required": False, "default": "", "type": "float"},
        "Rc": {"label": "Radius of curvature (m)", "required": False, "default": "inf", "type": "float"},
        "xbeta": {"label": "Misalignment yaw (rad)", "required": False, "default": "0", "type": "float"},
        "ybeta": {"label": "Misalignment pitch (rad)", "required": False, "default": "0", "type": "float"},
        "plane": {"label": "Plane of incidence", "required": False, "default": "xz", "type": "str"},
        "misaligned": {"label": "Misaligned (True/False)", "required": False, "default": False, "type": "bool"},
        "angle": {"label": "Angle (°)", "required": False, "default": "0", "type": "float"}
    },
    "beamsplitter_old": {  # old beam splitter
        "name": {"label": "Name", "required": True, "default": "", "type": "str"},
        "R": {"label": "Reflectivity", "required": False, "default": "", "type": "float"},
        "T": {"label": "Transmissivity", "required": False, "default": "", "type": "float"},
        "L": {"label": "Loss", "required": False, "default": "", "type": "float"},
        "phi": {"label": "Microscopic tuning (°)", "required": False, "default": "", "type": "float"},
        "alpha": {"label": "Angle of incidence (°)", "required": False, "default": "", "type": "float"},
        "Rc": {"label": "Radius of curvature (m)", "required": False, "default": "inf", "type": "float"},
        "xbeta": {"label": "Misalignment yaw (rad)", "required": False, "default": "0", "type": "float"},
        "ybeta": {"label": "Misalignment pitch (rad)", "required": False, "default": "0", "type": "float"},
        "plane": {"label": "Plane of incidence", "required": False, "default": "xz", "type": "str"},
        "misaligned": {"label": "Misaligned (True/False)", "required": False, "default": False, "type": "bool"},
        "angle": {"label": "Angle (°)", "required": False, "default": "0", "type": "float"}
    },
    "mirror": {
        "name": {"label": "Name", "required": True, "default": "", "type": "str"},
        "R": {"label": "Reflectivity", "required": False, "default": 0.5, "type": "float"},
        "T": {"label": "Transmittance", "required": False, "default": 0.5, "type": "float"},
        "L": {"label": "Loss", "required": False, "default": 0.0, "type": "float"},
        "phi": {"label": "Tuning (°)", "required": False, "default": 0.0, "type": "float"},
        "Rc": {"label": "Radius of curvature (m)", "required": False, "default": "inf", "type": "float"},
        "xbeta": {"label": "Misalignment yaw (rad)", "required": False, "default": "0", "type": "float"},
        "ybeta": {"label": "Misalignment pitch (rad)", "required": False, "default": "0", "type": "float"},
        "misaligned": {"label": "Misaligned (True/False)", "required": False, "default": False, "type": "bool"},
        "angle": {"label": "Angle (°)", "required": False, "default": "0", "type": "float"}
    },
    "laser": {
        "name": {"label": "Name", "required": True, "default": "", "type": "str"},
        "P": {"label": "Power (W)", "required": False, "default": 1, "type": "float"},
        "f": {"label": "Frequency offset (Hz)", "required": False, "default": 0, "type": "float"},
        "phase": {"label": "Phase offset", "required": False, "default": 0, "type": "float"},
        "signals_only": {"label": "Signals only (True/False)", "required": False, "default": False, "type": "bool"},
        "angle": {"label": "Angle (°)", "required": False, "default": "0", "type": "float"}
    },
    "power_detector": {
        "name": {"label": "Name", "required": True, "default": "", "type": "str"},
        "node": {"label": "Node", "required": True, "default": "", "type": "str"},
        "angle": {"label": "Angle (°)", "required": False, "default": "0", "type": "float"}
    },
}

##############################################################################
#                             Undo/Redo Commands                             #
##############################################################################
class AddItemCommand(QUndoCommand):
    def __init__(self, scene, item, description="Add Item"):
        super().__init__(description)
        self.scene = scene
        self.item = item
    def undo(self):
        self.scene.removeItem(self.item)
    def redo(self):
        self.scene.addItem(self.item)

class RemoveItemCommand(QUndoCommand):
    def __init__(self, scene, item, description="Remove Item"):
        super().__init__(description)
        self.scene = scene
        self.item = item
        self.original_pos = item.pos()
        self.original_parent = item.parentItem()
    def undo(self):
        if self.original_parent:
            self.item.setParentItem(self.original_parent)
        else:
            self.scene.addItem(self.item)
        self.item.setPos(self.original_pos)
    def redo(self):
        self.scene.removeItem(self.item)

##############################################################################
#                Properties Dialog for Optical Components                  #
##############################################################################
class PropertiesDialog(QDialog):
    def __init__(self, comp_type, current_values, prop_defs, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit properties: {comp_type}")
        self.prop_defs = prop_defs
        self.widgets = {}
        layout = QVBoxLayout()
        form = QFormLayout()
        # Add all properties except "angle"
        for key, definition in prop_defs.items():
            if key == "angle":
                continue
            field_type = definition.get("type", "str")
            default = definition.get("default", "")
            current = current_values.get(key, default) if current_values else default
            if field_type == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(current))
            else:
                widget = QLineEdit()
                widget.setText(str(current))
            self.widgets[key] = widget
            form.addRow(definition.get("label", key), widget)
        # Add the "angle" property at the bottom in blue
        if "angle" in prop_defs:
            definition = prop_defs["angle"]
            field_type = definition.get("type", "str")
            default = definition.get("default", "")
            current = current_values.get("angle", default) if current_values else default
            if field_type == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(current))
            else:
                widget = QLineEdit()
                widget.setText(str(current))
                widget.setStyleSheet("color: blue;")
            self.widgets["angle"] = widget
            form.addRow(definition.get("label", "Angle (°)"), widget)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
    def getValues(self):
        result = {}
        for key, widget in self.widgets.items():
            field_type = self.prop_defs[key].get("type", "str")
            if field_type == "bool":
                result[key] = widget.isChecked()
            else:
                text = widget.text().strip()
                if field_type == "int":
                    try:
                        result[key] = int(text) if text != "" else None
                    except ValueError:
                        result[key] = None
                elif field_type == "float":
                    try:
                        if text.lower() in ["inf", "infty"]:
                            result[key] = float('inf')
                        elif text == "":
                            result[key] = None
                        else:
                            result[key] = float(text)
                    except ValueError:
                        result[key] = None
                else:
                    result[key] = text
        return result

##############################################################################
#               Ports, Components, and ConnectionLine Classes                #
##############################################################################
PORT_POSITIONS = {
    "BS": {
        "p1": (0.0, 0.45),
        "p2": (0.0, 0.55),
        "p3": (1.0, 0.45),
        "p4": (1.0, 0.55),
    },
    "beamsplitter_old": {
        "p1": (0.5, 0.0),
        "p2": (0.5, 1.0),
        "p3": (0.0, 0.5),
        "p4": (1.0, 0.5),
    },
    "lens": {
        "p1": (0.0, 0.5),
        "p2": (1.0, 0.5),
    },
    "mirror": {
        "p1": (0.0, 0.5),
        "p2": (1.0, 0.5),
    },
    "laser": {
        "p1": (1.0, 0.5),
    },
    "power_detector": {
        "p1": (0.0, 0.5),
    },
}

class ConnectionLine(QGraphicsLineItem):
    def __init__(self, portA, portB):
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        pen = QPen(Qt.red, 2)
        self.setPen(pen)
        self.portA = portA
        self.portB = portB
        portA.connected_lines.append(self)
        portB.connected_lines.append(self)
        self.updateLinePosition()
    def updateLinePosition(self):
        ptA = self.portA.mapToScene(self.portA.boundingRect().center())
        ptB = self.portB.mapToScene(self.portB.boundingRect().center())
        self.setLine(ptA.x(), ptA.y(), ptB.x(), ptB.y())
    def removeFromPorts(self):
        if self in self.portA.connected_lines:
            self.portA.connected_lines.remove(self)
        if self in self.portB.connected_lines:
            self.portB.connected_lines.remove(self)

class PortItem(QGraphicsEllipseItem):
    def __init__(self, parent_component, port_name, radius=6):
        super().__init__()
        self.parent_component = parent_component
        self.port_name = port_name
        self.radius = radius
        self.setRect(0, 0, radius * 2, radius * 2)
        self.setBrush(QBrush(Qt.red, Qt.SolidPattern))
        self.setPen(QPen(Qt.white, 1))
        self.connected_lines = []
        self.setVisible(False)
        self.setZValue(10)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        scene = self.scene()
        if hasattr(scene, "portClicked"):
            scene.portClicked(self)

class OpticalComponent(QGraphicsPixmapItem):
    def __init__(self, pixmap, comp_type):
        super().__init__(pixmap)
        self.comp_type = comp_type
        self.rotation_angle = 0.0
        self.component_label = ""
        self.properties = {}
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        self.ports = []
        if comp_type in PORT_POSITIONS:
            for pname, (nx, ny) in PORT_POSITIONS[comp_type].items():
                p = PortItem(self, pname)
                p.setParentItem(self)
                self.ports.append(p)
            self.updatePortsPosition()
    def updatePortsPosition(self):
        if self.comp_type not in PORT_POSITIONS:
            return
        rect = self.pixmap().rect()
        for port_item in self.ports:
            nx, ny = PORT_POSITIONS[self.comp_type][port_item.port_name]
            px = rect.width() * nx
            py = rect.height() * ny
            port_item.setPos(px - port_item.radius, py - port_item.radius)
    def itemChange(self, change, value):
        if change in (QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemTransformHasChanged):
            for port in self.ports:
                for line in port.connected_lines:
                    line.updateLinePosition()
        elif change == QGraphicsItem.ItemSelectedHasChanged:
            for port in self.ports:
                port.setVisible(bool(value))
        return super().itemChange(change, value)
    def setAngle(self, angle_degrees):
        self.rotation_angle = angle_degrees
        transform = QTransform()
        transform.rotate(angle_degrees)
        self.setTransform(transform)
        for port in self.ports:
            for line in port.connected_lines:
                line.updateLinePosition()

##############################################################################
#              Custom Graphics Scene to Handle Placement and Port Clicks     #
##############################################################################
class MyGraphicsScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pending_port = None

    def mousePressEvent(self, event):
        main_window = self.parent()
        if hasattr(main_window, 'current_comp_to_place') and main_window.current_comp_to_place is not None:
            comp_type = main_window.current_comp_to_place
            pixmap = main_window.images.get(comp_type)
            if pixmap is not None:
                comp = OpticalComponent(pixmap, comp_type)
                comp.setPos(event.scenePos())
                self.addItem(comp)
                main_window.current_comp_to_place = None  # Reset selection after placing
                return  # Consume the event
        super().mousePressEvent(event)

    def portClicked(self, port):
        if self.pending_port is None:
            self.pending_port = port
        else:
            if self.pending_port != port:
                connection = ConnectionLine(self.pending_port, port)
                self.addItem(connection)
            self.pending_port = None

##############################################################################
#                      Assistant Widget (OpenAI Assistant API)             #
##############################################################################
class AssistantWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        title = QLabel("Assistant")
        layout.addWidget(title)
        self.conversation = QPlainTextEdit()
        self.conversation.setReadOnly(True)
        layout.addWidget(self.conversation)
        h_layout = QHBoxLayout()
        self.input_line = QLineEdit()
        h_layout.addWidget(self.input_line)
        self.send_button = QPushButton("Send")
        h_layout.addWidget(self.send_button)
        layout.addLayout(h_layout)
        self.send_button.clicked.connect(self.send_message)
        from openai import OpenAI
        self.client = OpenAI(api_key='')
        thread = self.client.beta.threads.create()
        self.thread_id = thread.id
        self.assistant_id = "asst_kgr19shqp0uwRR3rkmW1EfeV"
        self.conversation.appendPlainText("Assistant thread created. Thread ID: " + self.thread_id)
    def send_message(self):
        user_text = self.input_line.text().strip()
        if not user_text:
            return
        self.conversation.appendPlainText("User: " + user_text)
        self.input_line.clear()
        response = self.call_assistant_api(user_text)
        self.conversation.appendPlainText("Assistant: " + response)
    def call_assistant_api(self, user_text):
        try:
            self.client.beta.threads.messages.create(
                thread_id=self.thread_id,
                role="user",
                content=user_text
            )
            run = self.client.beta.threads.runs.create_and_poll(
                thread_id=self.thread_id,
                assistant_id=self.assistant_id,
                instructions="Please address the user as Jane Doe. The user has a premium account."
            )
            if run.status == "completed":
                messages = self.client.beta.threads.messages.list(thread_id=self.thread_id)
                assistant_response = ""
                for msg in messages.data:
                    if msg.role == "assistant":
                        if isinstance(msg.content, list):
                            for block in msg.content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    assistant_response += block.get("text", {}).get("value", "")
                                elif isinstance(block, str):
                                    assistant_response += block
                        else:
                            assistant_response += str(msg.content)
                return assistant_response if assistant_response else "No response received."
            else:
                return "Run did not complete: " + run.status
        except Exception as e:
            return "Error: " + str(e)

##############################################################################
#                           Custom Graphics View                             #
##############################################################################
class CustomGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)

##############################################################################
#                              Main Window                                 #
##############################################################################
class OpticalSetupGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Optical Layout Editor (Real-Time Movement)")
        self.setGeometry(100, 100, 1200, 800)
        self.undo_stack = QUndoStack(self)
        QShortcut(QKeySequence.Undo, self).activated.connect(self.undo_stack.undo)
        QShortcut(QKeySequence.Redo, self).activated.connect(self.undo_stack.redo)
        # Shortcut for Delete key to remove selected items
        QShortcut(QKeySequence.Delete, self).activated.connect(self.delete_selected)
        
        self.current_comp_to_place = None
        self.component_counts = {}
        
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        self.setCentralWidget(central_widget)
        
        # Top row: Left column (Palette), Center (Canvas), Right column (Assistant)
        top_row = QHBoxLayout()
        main_layout.addLayout(top_row)
        
        # Left column: Palette buttons
        left_layout = QVBoxLayout()
        top_row.addLayout(left_layout, 0)
        self.images = {
            "lens": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/b-lens2.png"),
            "BS": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/b-bspcube.png"),
            "beamsplitter_old": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/b-bsp.png"),
            "mirror": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/b-mir.png"),
            "laser": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/c-laser1.png"),
            "power_detector": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/e-pd1.png"),
            "faraday_isolator": self.load_image("/Users/ligo/Desktop/ComponentLibrary_files/png/c-isolator.png"),
        }
        for comp_name, pix in self.images.items():
            btn = QPushButton(comp_name)
            btn.setIcon(QIcon(pix))
            btn.setIconSize(pix.size())
            btn.clicked.connect(lambda _, c=comp_name: self.pick_component(c))
            left_layout.addWidget(btn)
        
        # Center column: Canvas using MyGraphicsScene
        self.scene = MyGraphicsScene(self)
        self.view = CustomGraphicsView(self.scene, self)
        top_row.addWidget(self.view, 1)
        
        # Right column: Assistant Widget (moved from bottom row)
        self.assistant_widget = AssistantWidget()
        top_row.addWidget(self.assistant_widget, 0)
        
        # Bottom row: Connection Details
        bottom_layout = QVBoxLayout()
        main_layout.addLayout(bottom_layout)
        bottom_label = QLabel("Connection Details")
        bottom_layout.addWidget(bottom_label)
        self.connection_list = QListWidget()
        self.connection_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        bottom_layout.addWidget(self.connection_list)
        copy_shortcut = QShortcut(QKeySequence.Copy, self.connection_list)
        copy_shortcut.activated.connect(self.copy_connection_details)
        
        self.draw_grid()
    
    def delete_selected(self):
        # Remove all selected items from the scene.
        for item in self.scene.selectedItems():
            self.scene.removeItem(item)
    
    def copy_connection_details(self):
        selected_items = self.connection_list.selectedItems()
        if selected_items:
            texts = [item.text() for item in selected_items]
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(texts))
            print("[INFO] Copied connection details to clipboard.")
    
    def draw_grid(self):
        pen = QPen(Qt.gray, 1)
        step = 50
        for x in range(0, 2000, step):
            self.scene.addLine(x, 0, x, 2000, pen)
        for y in range(0, 2000, step):
            self.scene.addLine(0, y, 2000, y, pen)
    
    def load_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            print(f"Warning: could not load image at {path}")
        return pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def pick_component(self, comp_name):
        self.current_comp_to_place = comp_name
        print(f"[INFO] Next click will place component: {comp_name}")
    
    def get_next_component_count(self, comp_name):
        if comp_name not in self.component_counts:
            self.component_counts[comp_name] = 1
        else:
            self.component_counts[comp_name] += 1
        return self.component_counts[comp_name]
    
    def get_label_for_component(self, comp_name, count):
        if comp_name == "BS":
            return f"BS{count}"
        elif comp_name == "beamsplitter_old":
            return f"Old BS {count}"
        else:
            return f"{comp_name.capitalize()} {count}"
    
    def get_component_display_label(self, comp):
        label = comp.component_label if comp.component_label else comp.comp_type
        changed = []
        for key, value in comp.properties.items():
            if key in ("name", "angle"):
                continue
            changed.append(f"{key}={value}")
        if changed:
            label += " (" + ", ".join(changed) + ")"
        return label
    
    def update_connection_details(self):
        self.connection_list.clear()
        for item in self.scene.items():
            if isinstance(item, ConnectionLine):
                portA = item.portA
                portB = item.portB
                compA = portA.parent_component
                compB = portB.parent_component
                labelA = self.get_component_display_label(compA)
                labelB = self.get_component_display_label(compB)
                connection_text = f"{labelA} {portA.port_name} - connected to {labelB} {portB.port_name}"
                self.connection_list.addItem(connection_text)

##############################################################################
#                              Main Application                            #
##############################################################################
def main():
    app = QApplication(sys.argv)
    window = OpticalSetupGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

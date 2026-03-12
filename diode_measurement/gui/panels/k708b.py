from collections.abc import Iterable
from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["K708BPanel"]


class K708BPanel(InstrumentPanel):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K708B", parent)

        # Channels

        self.slots_tab_widgets = QtWidgets.QTabWidget(self)

        # Generate channels, 1 slot, 8 rows, 12 columns
        slots = [1]
        rows = ["A", "B", "C", "D", "E", "F", "G", "H"]
        columns = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}
        for slot in slots:
            slot_widget = QtWidgets.QWidget()
            channels_layout = QtWidgets.QGridLayout(slot_widget)
            # Vertical row header
            for y, row in enumerate(rows):
                channels_layout.addWidget(QtWidgets.QLabel(f"{slot}{row}"), y + 1, 0)
            # Horizontal column header
            for x, column in enumerate(columns):
                channels_layout.addWidget(QtWidgets.QLabel(f"{column:02d}"), 0, x + 1)
            # Channel check boxes
            for y, row in enumerate(rows):
                for x, column in enumerate(columns):
                    channel = f"{slot}{row}{column:02d}"
                    check_box = QtWidgets.QCheckBox(slot_widget)
                    check_box.setToolTip(channel)
                    check_box.setStatusTip(f"Channel {channel}")
                    self.channel_check_boxes[channel] = check_box
                    channels_layout.addWidget(check_box, y + 1, x + 1)
            channels_layout.setRowStretch(len(rows) + 1, 1)
            channels_layout.setColumnStretch(len(columns) + 1, 1)
            self.slots_tab_widgets.addTab(slot_widget, f"Slot {slot}")

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_group_box_layout = QtWidgets.QVBoxLayout(self.channels_group_box)
        channels_group_box_layout.addWidget(self.slots_tab_widgets)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)
        left_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)

        # Parameters

        self.bind_parameter(
            "channels", MethodParameter(self.closed_channels, self.set_closed_channels)
        )

        self.restore_defaults()

    def closed_channels(self) -> list[str]:
        channels: list[str] = []
        for channel, check_box in self.channel_check_boxes.items():
            if check_box.isChecked():
                channels.append(channel)
        return channels

    def set_closed_channels(self, channels: Iterable[str]) -> None:
        selected = set(channels)
        for channel, check_box in self.channel_check_boxes.items():
            check_box.setChecked(channel in selected)

    def restore_defaults(self) -> None:
        self.set_closed_channels([])

    def set_locked(self, state: bool) -> None:
        self.slots_tab_widgets.setEnabled(not state)

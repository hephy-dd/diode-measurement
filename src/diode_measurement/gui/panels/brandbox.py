from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["BrandBoxPanel"]


class BrandBoxPanel(InstrumentPanel):
    CHANNELS: list[str] = ["A1", "B1", "C1", "A2", "B2", "C2"]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("BrandBox", parent)

        # Channels

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_layout = QtWidgets.QGridLayout(self.channels_group_box)

        # Create and place checkboxes in the grid
        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}
        for i, channel in enumerate(self.CHANNELS):
            check_box = QtWidgets.QCheckBox()
            check_box.setText(channel)
            check_box.setStatusTip(channel)
            self.channel_check_boxes[channel] = check_box
            channels_layout.addWidget(check_box, i // 3, i % 3)
        channels_layout.setColumnStretch(3, 1)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)
        left_layout.addStretch()

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)
        layout.setStretch(1, 1)

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

    def set_closed_channels(self, channels: list[str]) -> None:
        selected = set(channels)
        for channel, check_box in self.channel_check_boxes.items():
            check_box.setChecked(channel in selected)

    def restore_defaults(self) -> None:
        self.set_closed_channels([])

    def set_locked(self, state: bool) -> None:
        for check_box in self.channel_check_boxes.values():
            check_box.setEnabled(not state)

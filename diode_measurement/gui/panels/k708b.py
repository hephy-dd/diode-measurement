from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["K708BPanel"]


class K708BPanel(InstrumentPanel):
    CHANNELS: list[str] = [
        "1A00", "1A01", "1A02", "1A03", "1A04", "1A05", "1A06", "1A07", "1A08",
        "1B00", "1B01", "1B02", "1B03", "1B04", "1B05", "1B06", "1B07", "1B08",
        "1C00", "1C01", "1C02", "1C03", "1C04", "1C05", "1C06", "1C07", "1C08",
        "1D00", "1D01", "1D02", "1D03", "1D04", "1D05", "1D06", "1D07", "1D08",
        "1E00", "1E01", "1E02", "1E03", "1E04", "1E05", "1E06", "1E07", "1E08",
        "1F00", "1F01", "1F02", "1F03", "1F04", "1F05", "1F06", "1F07", "1F08",
        "1G00", "1G01", "1G02", "1G03", "1G04", "1G05", "1G06", "1G07", "1G08",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K708B", parent)

        # Channels

        self.channel_check_boxes: dict[str, QtWidgets.QCheckBox] = {}

        self.scroll_container = QtWidgets.QWidget()
        channels_layout = QtWidgets.QGridLayout(self.scroll_container)

        # Create and place checkboxes in the grid
        for i, channel in enumerate(self.CHANNELS):
            check_box = QtWidgets.QCheckBox()
            check_box.setText(channel)
            check_box.setStatusTip(channel)
            self.channel_check_boxes[channel] = check_box

            row = i // 9  # 9 per row
            col = i % 9
            channels_layout.addWidget(check_box, row, col)

        self.scroll_area = QtWidgets.QScrollArea()
        # self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_container)

        self.channels_group_box = QtWidgets.QGroupBox("Channels")

        channels_group_box_layout = QtWidgets.QVBoxLayout(self.channels_group_box)
        channels_group_box_layout.addWidget(self.scroll_area)

        # Layout

        left_layout = QtWidgets.QVBoxLayout()
        left_layout.addWidget(self.channels_group_box)
        left_layout.addStretch()
        left_layout.setStretch(0, 2)
        left_layout.setStretch(1, 1)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(left_layout)
        layout.addStretch()
        layout.setStretch(0, 1)

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
        self.scroll_container.setEnabled(not state)

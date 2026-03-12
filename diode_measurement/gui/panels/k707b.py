from typing import Optional

from PySide6 import QtWidgets

from ..panel import InstrumentPanel, MethodParameter

__all__ = ["K707BPanel"]


class K707BPanel(InstrumentPanel):
    CHANNELS: list[str] = [
        "1A01", "1A02", "1A03", "1A04", "1A05", "1A06", "1A07", "1A08", "1A09", "1A11", "1A12",
        "1B01", "1B02", "1B03", "1B04", "1B05", "1B06", "1B07", "1B08", "1B09", "1B11", "1B12",
        "1C01", "1C02", "1C03", "1C04", "1C05", "1C06", "1C07", "1C08", "1C09", "1C11", "1C12",
        "1D01", "1D02", "1D03", "1D04", "1D05", "1D06", "1D07", "1D08", "1D09", "1D11", "1D12",
        "1E01", "1E02", "1E03", "1E04", "1E05", "1E06", "1E07", "1E08", "1E09", "1E11", "1E12",
        "1F01", "1F02", "1F03", "1F04", "1F05", "1F06", "1F07", "1F08", "1F09", "1F11", "1F12",
        "1G01", "1G02", "1G03", "1G04", "1G05", "1G06", "1G07", "1G08", "1G09", "1G11", "1G12",
        "2A01", "2A02", "2A03", "2A04", "2A05", "2A06", "2A07", "2A08", "2A09", "2A11", "2A12",
        "2B01", "2B02", "2B03", "2B04", "2B05", "2B06", "2B07", "2B08", "2B09", "2B11", "2B12",
        "2C01", "2C02", "2C03", "2C04", "2C05", "2C06", "2C07", "2C08", "2C09", "2C11", "2C12",
        "2D01", "2D02", "2D03", "2D04", "2D05", "2D06", "2D07", "2D08", "2D09", "2D11", "2D12",
        "2E01", "2E02", "2E03", "2E04", "2E05", "2E06", "2E07", "2E08", "2E09", "2E11", "2E12",
        "2F01", "2F02", "2F03", "2F04", "2F05", "2F06", "2F07", "2F08", "2F09", "2F11", "2F12",
        "2G01", "2G02", "2G03", "2G04", "2G05", "2G06", "2G07", "2G08", "2G09", "2G11", "2G12",
        "3A01", "3A02", "3A03", "3A04", "3A05", "3A06", "3A07", "3A08", "3A09", "3A11", "3A12",
        "3B01", "3B02", "3B03", "3B04", "3B05", "3B06", "3B07", "3B08", "3B09", "3B11", "3B12",
        "3C01", "3C02", "3C03", "3C04", "3C05", "3C06", "3C07", "3C08", "3C09", "3C11", "3C12",
        "3D01", "3D02", "3D03", "3D04", "3D05", "3D06", "3D07", "3D08", "3D09", "3D11", "3D12",
        "3E01", "3E02", "3E03", "3E04", "3E05", "3E06", "3E07", "3E08", "3E09", "3E11", "3E12",
        "3F01", "3F02", "3F03", "3F04", "3F05", "3F06", "3F07", "3F08", "3F09", "3F11", "3F12",
        "3G01", "3G02", "3G03", "3G04", "3G05", "3G06", "3G07", "3G08", "3G09", "3G11", "3G12",
        "4A01", "4A02", "4A03", "4A04", "4A05", "4A06", "4A07", "4A08", "4A09", "4A11", "4A12",
        "4B01", "4B02", "4B03", "4B04", "4B05", "4B06", "4B07", "4B08", "4B09", "4B11", "4B12",
        "4C01", "4C02", "4C03", "4C04", "4C05", "4C06", "4C07", "4C08", "4C09", "4C11", "4C12",
        "4D01", "4D02", "4D03", "4D04", "4D05", "4D06", "4D07", "4D08", "4D09", "4D11", "4D12",
        "4E01", "4E02", "4E03", "4E04", "4E05", "4E06", "4E07", "4E08", "4E09", "4E11", "4E12",
        "4F01", "4F02", "4F03", "4F04", "4F05", "4F06", "4F07", "4F08", "4F09", "4F11", "4F12",
        "4G01", "4G02", "4G03", "4G04", "4G05", "4G06", "4G07", "4G08", "4G09", "4G11", "4G12",
    ]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("K707B", parent)

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

            row = i // 11  # 11 per row
            col = i % 11
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

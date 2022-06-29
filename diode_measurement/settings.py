__all__ = ["DEFAULTS"]

DEFAULTS = [
    {
        "id": "iv",
        "type": "iv",
        "title": "IV",
        "instruments": ["SMU", "ELM"],
        "default_instruments": ["SMU"],
        "default_begin_voltage": 0.0,
        "default_end_voltage": -300.0,
        "default_step_voltage": 5.0,
        "default_waiting_time": 0.5,
        "default_current_compliance": 10.0e-6,
        "voltage_unit": "V",
        "current_compliance_unit": "uA",
    },
    {
        "id": "cv_diode",
        "type": "cv",
        "title": "CV Diode",
        "instruments": ["SMU", "LCR"],
        "default_instruments": ["SMU", "LCR"],
        "default_begin_voltage": 0.0,
        "default_end_voltage": 50.0,
        "default_step_voltage": 1.0,
        "default_waiting_time": 0.3,
        "default_current_compliance": 100.0e-6,
        "voltage_unit": "V",
        "current_compliance_unit": "uA",
    },
    {
        "id": "cv_mos",
        "type": "cv",
        "title": "CV MOS",
        "instruments": ["LCR"],
        "default_instruments": ["LCR"],
        "default_begin_voltage": -10.0,
        "default_end_voltage": 10.0,
        "default_step_voltage": 1.0,
        "default_waiting_time": 1.0,
        "default_current_compliance": 10.0e-9,
        "voltage_unit": "V",
        "current_compliance_unit": "nA",
    },
]

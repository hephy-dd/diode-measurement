from diode_measurement.core.events import EventHandler

def test_event_handler():
    results = []
    handler = EventHandler()
    handler.subscribe(results.append)
    handler("spam")
    handler("cheeseshop")
    assert results == ["spam", "cheeseshop"]

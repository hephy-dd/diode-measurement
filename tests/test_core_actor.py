from diode_measurement.core.actor import ThreadingActor


def test_threading_actor():
    actor = ThreadingActor()
    actor.on_message = lambda message: f"{message}!"
    actor.start()

    try:
        assert actor.ask("Shrubbery").result() == "Shrubbery!"
        assert actor.ask("Ni").result() == "Ni!"
    finally:
        actor.stop(timeout=1.0)

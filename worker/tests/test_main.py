import asyncio

from app.main import main, register_shutdown_handlers


def test_main_module_imports_safely() -> None:
    import app.main  # noqa: F401

    assert True


def test_main_is_callable() -> None:
    assert callable(main)


def test_register_shutdown_handlers_does_not_crash() -> None:
    loop = asyncio.new_event_loop()
    try:
        shutdown_event = asyncio.Event()
        register_shutdown_handlers(loop, shutdown_event)
        assert not shutdown_event.is_set()
    except NotImplementedError:
        pass
    finally:
        loop.close()

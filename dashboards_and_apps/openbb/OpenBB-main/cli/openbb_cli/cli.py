"""OpenBB Platform CLI entry point."""

import sys

from openbb_cli.utils.utils import change_logging_sub_app, reset_logging_sub_app


def main():
    """Use the main entry point for the OpenBB Platform CLI."""
    print("Loading...\n")  # noqa: T201

    # pylint: disable=import-outside-toplevel
    from openbb_cli.config.setup import bootstrap
    from openbb_cli.controllers.cli_controller import launch

    bootstrap()

    dev = "--dev" in sys.argv[1:]
    debug = "--debug" in sys.argv[1:]

    launch(dev, debug)


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    initial_logging_sub_app = change_logging_sub_app()

    import os
    os.environ["OPENBB_AUTO_BUILD"] = "False"
    print("DEBUG: Patching provider_interface...")
    from importlib.metadata import entry_points
    print(f"DEBUG: Entry points found: {len(entry_points())}")
    for group in ["openbb_core_extension", "openbb_provider_extension", "openbb_obbject_extension"]:
        eps = entry_points(group=group)
        print(f"DEBUG: Group {group}: {len(eps)} entries")
        if len(eps) > 0:
            print(f"DEBUG: Sample: {list(eps)[0]}")

    # PATCH: Inject dynamic OBBject types into provider_interface for frozen app support
    try:
        from openbb_core.app.provider_interface import ProviderInterface
        import openbb_core.app.provider_interface as pi_module
        pi = ProviderInterface()
        for name, cls in pi.return_annotations.items():
            setattr(pi_module, f"OBBject_{name}", cls)
        print(f"DEBUG: Successfully injected {len(pi.return_annotations)} dynamic OBBject types.")
        print(f"DEBUG: Keys: {list(pi.return_annotations.keys())}")
        print(f"DEBUG: Module attributes (sample): {dir(pi_module)[:20]}")
        import sys
        sys.stdout.flush()
    except Exception as e:
        print(f"DEBUG: Failed to inject OBBject types: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.stdout.flush()

    try:
        main()
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter to close...")
    finally:
        reset_logging_sub_app(initial_logging_sub_app)

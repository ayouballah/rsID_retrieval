"""
Main entry point for rsID retrieval application.
Provides GUI, CLI, and Sandbox interfaces.
"""
import sys
import argparse


def main():
    """
    Main entry point that decides whether to launch GUI, CLI, or Sandbox mode.
    """
    # Check for unified GUI mode
    if '--unified' in sys.argv or '--unified-gui' in sys.argv:
        # Launch unified GUI with both regular and sandbox modes
        from unified_gui import main as unified_gui_main
        unified_gui_main()
    elif '--sandbox' in sys.argv:
        # Remove --sandbox from args and check for CLI vs GUI
        sys.argv.remove('--sandbox')
        if len(sys.argv) == 1 or '--gui' in sys.argv:
            # Launch Sandbox GUI
            from sandbox_gui import main as sandbox_gui_main
            sandbox_gui_main()
        else:
            # Launch Sandbox CLI
            from sandbox_cli import main as sandbox_cli_main
            sandbox_cli_main()
    elif len(sys.argv) == 1 or '--gui' in sys.argv:
        # Launch unified GUI by default (best user experience)
        from unified_gui import main as unified_gui_main
        unified_gui_main()
    else:
        # Launch regular CLI
        from cli import main as cli_main
        cli_main()


if __name__ == "__main__":
    main()

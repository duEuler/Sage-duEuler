import sys

from runtime.ui_desktop import main


if __name__ == "__main__":
    main(start_minimized="--minimized" in sys.argv)

import logging
import containerizer

# Import all of the comamnds
import containerizer.commands

# Configure the logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] : %(message)s"
)

# Launch the application
if __name__ == "__main__":
    containerizer.app(prog_name="docker-containerizer")

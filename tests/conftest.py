import os
import sys

# Make `import app` work when pytest is invoked from any directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

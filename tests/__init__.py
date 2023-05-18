import os
import sys

import vorta._version

resource_file = os.path.join(os.path.dirname(vorta._version.__file__), 'assets/icons')
sys.path.append(resource_file)

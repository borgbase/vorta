import sys
import os

import vorta.models
resource_file = os.path.join(os.path.dirname(vorta.models.__file__), 'assets/icons')
sys.path.append(resource_file)

import os
import subprocess
from pathlib import Path

from .common import install_test_addons


def test_addons_path():
    """Test must not fail where there are no installable addons."""
    assert (
        Path(os.environ["ODOO_RC"]).read_text()
        == "[options]\n"
    )
    with install_test_addons(["addon_success"]):
        content = Path(os.environ["ODOO_RC"]).read_text()
        
        # Should start with [options] and have addons_path
        assert content.startswith("[options]\naddons_path=")
        
        # Should include base addons directory
        assert "/opt/odoo/addons" in content
        
        # Should end with current directory
        assert content.endswith(",.\n")
        
        # Should be valid for odoo
        subprocess.check_call(["python", "-c", "import odoo.cli"])

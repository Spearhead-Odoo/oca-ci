import ast
import contextlib
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

ODOO_VENV = "/opt/odoo-venv"

test_addons_dir = Path(__file__).parent / "data" / "addons"

odoo_version_info = tuple(map(int, os.environ["ODOO_VERSION"].split(".")))

odoo_bin = "odoo"


@contextlib.contextmanager
def preserve_odoo_rc():
    odoo_rc_path = Path(os.environ["ODOO_RC"])
    odoo_rc = odoo_rc_path.read_bytes()
    try:
        yield
    finally:
        odoo_rc_path.write_bytes(odoo_rc)


@contextlib.contextmanager
def preserve_odoo_venv():
    subprocess.check_call(["cp", "-arl", ODOO_VENV, ODOO_VENV + ".org"])
    try:
        yield
    finally:
        subprocess.check_call(["rm", "-r", ODOO_VENV])
        subprocess.check_call(["mv", ODOO_VENV + ".org", ODOO_VENV])


@contextlib.contextmanager
def make_addons_dir(test_addons):
    """Copy test addons to a temporary directory.

    Adjust the addons version to match the Odoo version being tested.
    Rename __manifest__.py to __openerp__.py for older Odoo versions.
    Add pyproject.toml.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        for addon_name in test_addons:
            shutil.copytree(test_addons_dir / addon_name, tmppath / addon_name)
            # prefix Odoo version
            manifest_path = tmppath / addon_name / "__manifest__.py"
            manifest = ast.literal_eval(manifest_path.read_text())
            manifest["version"] = os.environ["ODOO_VERSION"] + "." + manifest["version"]
            manifest_path.write_text(repr(manifest))
            if odoo_version_info < (10, 0):
                manifest_path.rename(manifest_path.parent / "__openerp__.py")
            pyproject_toml_path = tmppath / addon_name / "pyproject.toml"
            pyproject_toml_path.write_text(
                textwrap.dedent(
                    """\
                    [build-system]
                    requires = ["whool"]
                    build-backend = "whool.buildapi"
                    """
                )
            )
        yield tmppath


@contextlib.contextmanager
def install_test_addons(test_addons):
    with preserve_odoo_rc(), preserve_odoo_venv(), make_addons_dir(
        test_addons
    ) as addons_dir:
        subprocess.check_call(["oca_install_addons"], cwd=addons_dir)
        yield addons_dir


def dropdb():
    subprocess.check_call(["dropdb", "--if-exists", os.environ["PGDATABASE"]])


def did_run_test_module(output, test_module):
    """Check that a test did run by looking in the Odoo log.

    test_module is the full name of the test (addon_name.tests.test_module).
    """
    return "odoo.addons." + test_module in output

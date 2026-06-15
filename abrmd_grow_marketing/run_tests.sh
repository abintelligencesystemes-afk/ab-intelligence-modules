#!/usr/bin/env bash
# Lance les tests pure-python (sans Odoo).
# Workaround : le module a un __init__.py qui importe `odoo`, ce qui
# perturbe la collection pytest. On copie les tests dans /tmp et on
# patche ROOT vers le module via une variable d'env.
set -euo pipefail

MODULE_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTDIR="$(mktemp -d -t abrmd_grow_test.XXXXXX)"
cp "${MODULE_DIR}/tests_pure/"*.py "${TESTDIR}/"

# Patche ROOT dans tous les fichiers test_*.py pour pointer vers le module
for f in "${TESTDIR}"/test_*.py; do
    sed -i.bak "s|pathlib.Path(__file__).resolve().parent.parent|pathlib.Path('${MODULE_DIR}')|g" "${f}"
done

cd "${TESTDIR}"
python -m pytest -v -p no:cacheprovider .
rc=$?
rm -rf "${TESTDIR}"
exit $rc

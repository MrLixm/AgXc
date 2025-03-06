THISDIR=$(dirname "$0")
cd "$THISDIR" || exit

ocio_path="$THISDIR/../../../../../ocio/AgXc_default_OCIO-v1/config.ocio"
"C:\Program Files\Nuke15.1v5\Nuke15.1.exe" --nc -t ./test_config.py "$ocio_path"
echo "------------------------------------------------------------------------"

ocio_path="$THISDIR/../../../../../ocio/AgXc_default_OCIO-v2/config.ocio"
"C:\Program Files\Nuke15.1v5\Nuke15.1.exe" --nc -t ./test_config.py "$ocio_path"
echo "------------------------------------------------------------------------"
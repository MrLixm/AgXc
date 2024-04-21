THISDIR=$(dirname "$0")
cd "$THISDIR" || exit

ocio_path="$THISDIR/../../../../../ocio/AgXc-v0.2.5_default_OCIO-v1/config.ocio"
"C:\Program Files\Nuke15.0v2\Nuke15.0.exe" --nc -t ./test_config.py "$ocio_path"
echo "------------------------------------------------------------------------"

ocio_path="$THISDIR/../../../../../ocio/AgXc-v0.2.5_default_OCIO-v2/config.ocio"
"C:\Program Files\Nuke15.0v2\Nuke15.0.exe" --nc -t ./test_config.py "$ocio_path"
echo "------------------------------------------------------------------------"
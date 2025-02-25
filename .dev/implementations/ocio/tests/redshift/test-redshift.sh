BASEDIR=$(dirname "$0")
cd "$BASEDIR" || exit 1

OCIOCONFIG="$BASEDIR/../../../../../ocio/AgXc_redshift_OCIO-v2/config.ocio"
if [ ! -f "$OCIOCONFIG" ]; then
    echo "ocio config file not found: $OCIOCONFIG"
    exit 2
fi

"C:\ProgramData\redshift\bin\redshiftCmdLine.exe" simplescene.v0001.rs \
-oip _outputs/ \
-ocioconfig "$OCIOCONFIG" \
-ociorenderspace "scene_linear" -ociodisplay "sRGB-2.2" -ocioview "AgXc.base"
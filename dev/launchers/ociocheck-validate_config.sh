# go to repo root assuming cwd is directory of this file
cd ../..
pwd

OCIOCHECK="/F/softwares/apps/ocio/v1/ocio_apps/ocio_apps/ociocheck.exe"

export OCIO="./ocio/config.ocio"

"$OCIOCHECK"
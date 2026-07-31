@ECHO OFF
SET SPHINXOPTS=-W --keep-going
SET SPHINXBUILD=python -m sphinx
SET SOURCEDIR=.
SET BUILDDIR=_build

IF "%1" == "clean" GOTO clean
IF "%1" == "html" GOTO html
GOTO help

:html
%SPHINXBUILD% %SPHINXOPTS% -b html "%SOURCEDIR%" "%BUILDDIR%\html"
GOTO end

:clean
rmdir /S /Q "%BUILDDIR%"
GOTO end

:help
ECHO Usage: make.bat [html^|clean]

:end

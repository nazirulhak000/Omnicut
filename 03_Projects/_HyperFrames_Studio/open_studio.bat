@echo off
rem Double-click to open HyperFrames Studio with every product's clips.
rem The browser opens by itself. Close this window to stop the studio.
cd /d "%~dp0"
npx --yes hyperframes@0.8.143 preview

#!/bin/bash

# --- Configuration Variables ---
APP_NAME="Vertex AI Client"
APP_IDENTIFIER="com.vertex.desktop"
APP_BUNDLE_NAME="${APP_NAME}.app" # This is the .app bundle name (e.g., "Vertex AI Client.app")
DIST_DIR="dist"
BUILD_DIR="build" # PyInstaller's intermediate build directory
DMG_OUTPUT_NAME="${APP_NAME}.dmg"
PKG_OUTPUT_NAME="${APP_NAME}.pkg"
RESOURCES_DIR="resources" # Directory for icon and other package resources
ICON_FILE="${RESOURCES_DIR}/icon.icns"
README_FILE="README.md" # Assuming README.md is in the project root

# Path to your main Python script for PyInstaller
MAIN_PYTHON_SCRIPT="src/vertex_desktop/main.py"

# Developer ID signing identity (REQUIRED for PKG distribution outside App Store)
DEVELOPER_ID_INSTALLER_IDENTITY="Developer ID Installer: Your Developer Name (XXXXXXXXXX)" # <--- *** CHANGE THIS! ***


# --- Pre-flight Checks and Setup ---
echo "--- Starting Package Creation Process ---"

# Check for required commands
command -v uv >/dev/null 2>&1 || { echo >&2 "Error: 'uv' is not installed. Aborting. Install with 'brew install uv'."; exit 1; }
command -v pyinstaller >/dev/null 2>&1 || { echo >&2 "Error: 'pyinstaller' is not installed. Aborting. Run 'uv pip install pyinstaller'."; exit 1; }
command -v create-dmg >/dev/null 2>&1 || { echo >&2 "Error: 'create-dmg' is not installed. Aborting. Run 'brew install create-dmg'."; exit 1; }
command -v pkgbuild >/dev/null 2>&1 || { echo >&2 "Error: 'pkgbuild' (Xcode Command Line Tools) is not found. Aborting. Run 'xcode-select --install'."; exit 1; }
command -v productbuild >/dev/null 2>&1 || { echo >&2 "Error: 'productbuild' (Xcode Command Line Tools) is not found. Aborting. Run 'xcode-select --install'."; exit 1; }

# Ensure resources directory exists
mkdir -p "${RESOURCES_DIR}"

# Ensure icon file exists
if [ ! -f "${ICON_FILE}" ]; then
    echo "Error: Icon file not found at '${ICON_FILE}'. Please place your icon.icns there."
    exit 1
fi

# Ensure main Python script exists
if [ ! -f "${MAIN_PYTHON_SCRIPT}" ]; then
    echo "Error: Main Python script not found at '${MAIN_PYTHON_SCRIPT}'. Please check the path and filename."
    exit 1
fi

# Ensure README file exists if you're adding it
if [ ! -f "${README_FILE}" ]; then
    echo "Warning: README.md not found at '${README_FILE}'. PyInstaller will proceed without it, but it might affect the DMG's appearance or PKG's included data."
fi

# --- Cleanup Previous Builds ---
echo "Cleaning up previous build artifacts..."

# --- AGGRESSIVE DMG UNMOUNTING ATTEMPT ---
# Loop to try and unmount the DMG a few times if it's still mounted.
# The volume name is usually the same as APP_NAME
MAX_UNMOUNT_ATTEMPTS=5
UNMOUNT_SLEEP_SECONDS=2

for i in $(seq 1 $MAX_UNMOUNT_ATTEMPTS); do
    if hdiutil info | grep -q "/Volumes/${APP_NAME}"; then
        echo "Attempt ${i}/${MAX_UNMOUNT_ATTEMPTS}: Unmounting existing '${APP_NAME}' disk image volume..."
        hdiutil detach "/Volumes/${APP_NAME}" -force
        if [ $? -eq 0 ]; then
            echo "Successfully unmounted /Volumes/${APP_NAME}."
            break # Exit loop on success
        else
            echo "Failed to unmount /Volumes/${APP_NAME}. Retrying in ${UNMOUNT_SLEEP_SECONDS} seconds..."
            sleep ${UNMOUNT_SLEEP_SECONDS}
        fi
    else
        echo "No mounted '${APP_NAME}' disk image found."
        break # No mounted DMG, exit loop
    fi
done

# Final check after unmount attempts
if hdiutil info | grep -q "/Volumes/${APP_NAME}"; then
    echo "Warning: Could not unmount '/Volumes/${APP_NAME}' after multiple attempts. This might cause 'create-dmg' to fail."
fi
# --- END AGGRESSIVE DMG UNMOUNTING ---


# Remove generated files and directories
rm -rf "${DIST_DIR}" "${BUILD_DIR}" "${PKG_OUTPUT_NAME}" "${DMG_OUTPUT_NAME}" "${APP_NAME}.spec"

# --- Install Dependencies ---
echo "Installing/updating Python dependencies with uv..."
uv pip install -e . pyinstaller

# --- Create the App Bundle with PyInstaller ---
echo "Creating the application bundle with PyInstaller..."
pyinstaller \
    --name "${APP_NAME}" \
    --windowed \
    --onedir \
    --icon "${ICON_FILE}" \
    --osx-bundle-identifier "${APP_IDENTIFIER}" \
    --add-data "${README_FILE}:." \
    "${MAIN_PYTHON_SCRIPT}"

# Store the exit status of PyInstaller
PYINSTALLER_EXIT_CODE=$?

# Define the full path to the .app bundle PyInstaller should create (directly in dist/)
APP_BUNDLE_FULL_PATH="${DIST_DIR}/${APP_BUNDLE_NAME}"

if [ ${PYINSTALLER_EXIT_CODE} -ne 0 ]; then
    echo "Error: PyInstaller command failed with exit code ${PYINSTALLER_EXIT_CODE}."
    echo "Check PyInstaller log file for details (usually in the 'build' directory, e.g., build/${APP_NAME}/warn-${APP_NAME}.txt)."
    exit 1
elif [ ! -d "${APP_BUNDLE_FULL_PATH}" ]; then
    echo "Error: PyInstaller reported success (exit code 0), but the app bundle was NOT found at expected path: '${APP_BUNDLE_FULL_PATH}'."
    echo "PyInstaller might have placed it elsewhere or encountered a hidden issue. Check logs carefully."
    echo "Contents of dist/ directory:"
    ls -l "${DIST_DIR}"
    exit 1
else
    echo "App bundle created successfully at: ${APP_BUNDLE_FULL_PATH}"
fi

# --- Create DMG Package ---
echo "Creating DMG package: ${DMG_OUTPUT_NAME}..."
# Adding a slightly longer sleep here, as create-dmg directly interacts with hdiutil
sleep 3

create-dmg \
    --volname "${APP_NAME}" \
    --volicon "${ICON_FILE}" \
    --window-pos 200 120 \
    --window-size 800 400 \
    --icon-size 100 \
    --icon "${APP_BUNDLE_NAME}" 200 190 \
    --hide-extension "${APP_BUNDLE_NAME}" \
    --app-drop-link 600 185 \
    "${DMG_OUTPUT_NAME}" \
    "${DIST_DIR}/" # Correct path: the directory containing the .app bundle (which is 'dist/')

if [ -f "${DMG_OUTPUT_NAME}" ]; then
    echo "DMG created: ${DMG_OUTPUT_NAME}"
else
    echo "Error: create-dmg failed to create ${DMG_OUTPUT_NAME}."
    echo "This is likely due to 'hdiutil: create failed - Resource busy' from a previous run."
    echo "If the problem persists, try a system reboot to clear any stubborn locks."
    exit 1
fi

# --- Create PKG Package ---
echo "Creating PKG package: ${PKG_OUTPUT_NAME}..."

# Check if Developer ID Installer identity is set correctly
if [ "${DEVELOPER_ID_INSTALLER_IDENTITY}" = "Developer ID Installer: Your Developer Name (XXXXXXXXXX)" ] || [ -z "${DEVELOPER_ID_INSTALLER_IDENTITY}" ]; then
    echo "Warning: Developer ID Installer identity is a placeholder or empty. PKG will NOT be signed."
    echo "To sign, replace 'Developer ID Installer: Your Developer Name (XXXXXXXXXX)' with your actual certificate name in the script."
    # Build unsigned PKG
    productbuild \
        --component "${APP_BUNDLE_FULL_PATH}" "/Applications" \
        --identifier "${APP_IDENTIFIER}" \
        --version "1.0.0" \
        "${PKG_OUTPUT_NAME}"
else
    # Build signed PKG
    echo "Attempting to sign PKG with identity: '${DEVELOPER_ID_INSTALLER_IDENTITY}'"
    productbuild \
        --component "${APP_BUNDLE_FULL_PATH}" "/Applications" \
        --identifier "${APP_IDENTIFIER}" \
        --version "1.0.0" \
        --sign "${DEVELOPER_ID_INSTALLER_IDENTITY}" \
        "${PKG_OUTPUT_NAME}"
fi

# Verify productbuild output
if [ -f "${PKG_OUTPUT_NAME}" ]; then
    echo "PKG created: ${PKG_OUTPUT_NAME}"
else
    echo "Error: productbuild failed to create ${PKG_OUTPUT_NAME}."
    echo "Check the signing identity or productbuild errors above."
    exit 1
fi

echo "--- Build process complete! ---"
echo "You can find your packages in the current directory:"
echo "- ${DMG_OUTPUT_NAME}"
echo "- ${PKG_OUTPUT_NAME}"

# Reminder for notarization
echo ""
echo "--- IMPORTANT ---"
echo "For distribution outside the Mac App Store, you should notarize your .dmg and .pkg files."
echo "Use 'xcrun notarytool submit <package_name> --apple-id <your_apple_id> --password <app_specific_password> --team-id <your_team_id>'"
echo "Refer to Apple's documentation on notarization for full details."

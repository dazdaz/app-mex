# Makefile
.PHONY: install run build dmg clean dev

install:
	uv pip install -r requirements.txt

run:
	uv run python vertex_desktop.py

build:
	uv pip install -r requirements-dev.txt
	pyinstaller vertex_desktop.spec

dmg: build
	# This command creates a professional-looking DMG with a background image,
	# a link to the Applications folder, and a custom volume name.
	# You may need to `npm install -g create-dmg` if not already installed.
	create-dmg \
		--volname "Vertex AI Client Installer" \
		--window-pos 200 120 \
		--window-size 600 380 \
		--icon-size 100 \
		--icon "Vertex AI Client.app" 175 170 \
		--hide-extension "Vertex AI Client.app" \
		--app-drop-link 425 170 \
		"dist/VertexAIClient.dmg" \
		"dist/Vertex AI Client.app"

clean:
	rm -rf build dist __pycache__ *.spec
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

dev:
	uv pip install -r requirements.txt -r requirements-dev.txt

spec:
	pyinstaller \
		--name "Vertex AI Client" \
		--windowed \
		--onefile \
		--osx-bundle-identifier com.vertex.desktop \
		vertex_desktop.py

# With .PHONY: build, Make ignores whether a file/folder called build exists and just runs the command every time.
.PHONY: build run clean test

build:
	cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
	cmake --build build -j

run: build
	./build/gameserver

clean:
	rm -rf build/

test:
	cmake --build build --target test

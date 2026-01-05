#pragma once

struct Config {
    int port = 9001;

    static Config FromEnv(int argc, char** argv);
};
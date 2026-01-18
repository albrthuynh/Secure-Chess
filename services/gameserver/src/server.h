#pragma once
#include "config.h"

class Server {
    public: 
        // explicit keyword prevents type conversions when making an object
        explicit Server(const Config& config);
        void run();
    
    private:
        Config config_;
};

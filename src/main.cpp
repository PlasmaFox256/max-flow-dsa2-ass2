#include "maxflow/io.hpp"
#include "maxflow/solver.hpp"
#include "maxflow/verify.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc != 5 || std::string(argv[1]) != "--algorithm" ||
            std::string(argv[3]) != "--input")
            throw std::invalid_argument(
                "usage: maxflow_run --algorithm edmonds_karp|push_relabel --input FILE");
        const std::string algorithm = argv[2];
        maxflow::Solver solve = nullptr;
        if (algorithm == "edmonds_karp") solve = maxflow::edmonds_karp;
        else if (algorithm == "push_relabel") solve = maxflow::push_relabel;
        else throw std::invalid_argument("unknown algorithm");
        std::ifstream input(argv[4]);
        if (!input) throw std::runtime_error("cannot open input file");
        auto instance = maxflow::read_instance(input);
        const auto start = std::chrono::steady_clock::now();
        const auto value = solve(instance.graph, instance.source, instance.sink);
        const auto end = std::chrono::steady_clock::now();
        maxflow::verify_max_flow(instance.graph, instance.source, instance.sink, value);
        const double seconds = std::chrono::duration<double>(end - start).count();
        std::cout << std::setprecision(17)
                  << "{\"status\":\"ok\",\"flow\":" << value
                  << ",\"seconds\":" << seconds << "}\n";
        return 0;
    } catch (const maxflow::NotImplemented&) {
        std::cout << "{\"status\":\"not_implemented\"}\n";
        return 3;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

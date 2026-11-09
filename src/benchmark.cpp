// Experiment harness only: neither solver is instrumented or modified.
#include "maxflow/io.hpp"
#include "maxflow/solver.hpp"
#include "maxflow/verify.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char **argv)
{
    try
    {
        if (argc != 4)
            throw std::invalid_argument(
                "usage: maxflow_bench ALGORITHM INPUT TARGET_SECONDS");
        const std::string algorithm = argv[1];
        maxflow::Solver solve = nullptr;
        if (algorithm == "edmonds_karp")
            solve = maxflow::edmonds_karp;
        else if (algorithm == "push_relabel")
            solve = maxflow::push_relabel;
        else
            throw std::invalid_argument("unknown algorithm");
        const double target = std::stod(argv[3]);
        if (!(target > 0 && target <= 1))
            throw std::invalid_argument("invalid target");
        std::ifstream input(argv[2]);
        if (!input)
            throw std::runtime_error("cannot open input");
        auto instance = maxflow::read_instance(input);
        // One untimed, verified warm-up per process. Residual state is reset
        // outside every interval; solver-local allocations remain timed.
        const auto expected = solve(instance.graph, instance.source, instance.sink);
        maxflow::verify_max_flow(instance.graph, instance.source, instance.sink, expected);
        double elapsed = 0;
        std::size_t iterations = 0;
        do
        {
            instance.graph.reset();
            const auto start = std::chrono::steady_clock::now();
            const auto flow = solve(instance.graph, instance.source, instance.sink);
            const auto stop = std::chrono::steady_clock::now();
            elapsed += std::chrono::duration<double>(stop - start).count();
            if (flow != expected)
                throw std::logic_error("inconsistent repeated flow");
            maxflow::verify_max_flow(instance.graph, instance.source, instance.sink, flow);
            ++iterations;
        } while (elapsed < target && iterations < 1024);
        std::cout << std::setprecision(17)
                  << "{\"status\":\"ok\",\"flow\":" << expected
                  << ",\"iterations\":" << iterations
                  << ",\"solver_seconds_total\":" << elapsed
                  << ",\"seconds\":" << elapsed / iterations << "}\n";
    }
    catch (const std::exception &error)
    {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

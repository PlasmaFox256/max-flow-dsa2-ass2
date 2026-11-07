#include "maxflow/io.hpp"
#include "maxflow/solver.hpp"
#include "maxflow/verify.hpp"
#include <algorithm>
#include <iostream>
#include <limits>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>

using namespace maxflow;
void require(bool condition) {
    if (!condition) throw std::runtime_error("test assertion failed");
}
template<class Function> void rejects(Function function) {
    bool rejected = false;
    try { function(); } catch (const std::exception&) { rejected = true; }
    require(rejected);
}
Capacity exhaustive_cut(const Graph& graph, Vertex source, Vertex sink) {
    Capacity best = std::numeric_limits<Capacity>::max();
    for (std::uint64_t mask = 0; mask < (std::uint64_t{1} << graph.vertex_count()); ++mask) {
        if (!(mask & (std::uint64_t{1} << source)) || (mask & (std::uint64_t{1} << sink))) continue;
        Capacity cut = 0;
        for (const auto& edge : graph.original_edges())
            if ((mask & (std::uint64_t{1} << edge.from)) && !(mask & (std::uint64_t{1} << edge.to)))
                cut += edge.capacity;
        best = std::min(best, cut);
    }
    return best;
}
void framework_tests() {
    Graph graph(3);
    graph.add_edge(0, 1, 3);
    graph.add_edge(0, 1, 2); // Parallel original edge owns a distinct pair.
    graph.add_edge(1, 0, 7); // Antiparallel original edge is independent.
    graph.add_edge(1, 2, 4);
    graph.add_edge(0, 2, 0);
    require(graph.original_edges()[2].forward == 4);
    rejects([&] { graph.push(0, 4); });
    rejects([&] { verify_max_flow(graph, 0, 2, 0); }); // Feasible but not maximum.
    graph.push(0, 3);
    rejects([&] { verify_max_flow(graph, 0, 2, 3); }); // Stranded excess.
    graph.push(2, 1);
    graph.push(6, 4);
    verify_max_flow(graph, 0, 2, 4);
    require(exhaustive_cut(graph, 0, 2) == 4);
    rejects([&] { verify_max_flow(graph, 0, 2, 3); });
    graph.push(Graph::reverse(0), 1);
    require(graph.edge(0).residual == 1);
    require(graph.edge(4).residual == 7);
    graph.reset();
    require(graph.edge(0).residual == 3 && graph.edge(1).residual == 0);
    rejects([&] { graph.add_edge(0, 0, 1); });
    rejects([&] { graph.add_edge(0, 3, 1); });
    rejects([&] { graph.add_edge(0, 1, -1); });
    Graph large(2);
    large.add_edge(0, 1, std::numeric_limits<Capacity>::max());
    rejects([&] { large.add_edge(0, 1, 1); });
    for (const std::string text : {"2 0 0 0", "2 1 0 1 0 1 -1", "2 1 0 1", "2 0 0 1 extra", "2 1 0 1 -1 1 2"}) {
        rejects([&] { std::istringstream input(text); read_instance(input); });
    }
    std::istringstream valid("3 2 0 2\n0 1 4\n1 2 4\n");
    const auto instance = read_instance(valid);
    require(instance.graph.original_edges().size() == 2);
    Graph disconnected(3);
    disconnected.add_edge(0, 1, 5);
    verify_max_flow(disconnected, 0, 2, 0);
}
void check_solver(Solver solve, Graph graph, Vertex source, Vertex sink) {
    const auto expected = exhaustive_cut(graph, source, sink);
    const auto result = solve(graph, source, sink);
    require(result == expected);
    verify_max_flow(graph, source, sink, result);
    graph.reset();
    require(solve(graph, source, sink) == expected);
    verify_max_flow(graph, source, sink, expected);
}
void solver_tests(Solver solve) {
    Graph basic(2);
    basic.add_edge(0, 1, 5);
    check_solver(solve, basic, 0, 1);
    Graph stranded(4);
    stranded.add_edge(0, 1, 100);
    stranded.add_edge(1, 2, 1);
    stranded.add_edge(2, 3, 1);
    check_solver(solve, stranded, 0, 3);
    Graph large(2);
    large.add_edge(0, 1, Capacity{1} << 40);
    check_solver(solve, large, 0, 1);
    std::mt19937 random(20261107);
    for (int trial = 0; trial < 250; ++trial) {
        const auto n = 2 + random() % 7;
        Graph graph(n);
        for (unsigned int i = 0; i < n * n; ++i) {
            const auto u = random() % n, v = random() % n;
            if (u != v && random() % 3 == 0) graph.add_edge(u, v, random() % 21);
        }
        const Vertex source = random() % n;
        const Vertex sink = (source + 1 + random() % (n - 1)) % n;
        check_solver(solve, graph, source, sink);
    }
}
int main(int argc, char** argv) {
    try {
        const std::string suite = argc > 1 ? argv[1] : "framework";
        if (suite == "framework") framework_tests();
        else if (suite == "edmonds_karp") solver_tests(edmonds_karp);
        else if (suite == "push_relabel") solver_tests(push_relabel);
        else throw std::runtime_error("unknown test suite");
        std::cout << suite << ": passed\n";
        return 0;
    } catch (const NotImplemented&) {
        std::cout << "SKIPPED: solver is not implemented\n";
        return 77;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

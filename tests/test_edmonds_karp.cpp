#include "maxflow/solver.hpp"
#include "maxflow/verify.hpp"
#include <algorithm>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <utility>

using namespace maxflow;

namespace {
void check(Graph graph, Vertex source, Vertex sink, Capacity expected) {
    for (int repeat = 0; repeat < 2; ++repeat) {
        const auto value = edmonds_karp(graph, source, sink);
        if (value != expected) throw std::runtime_error("unexpected Edmonds-Karp value");
        verify_max_flow(graph, source, sink, value);
        graph.reset();
    }
}

void boundary_cases() {
    check(Graph(2), 0, 1, 0);
    const auto maximum = std::numeric_limits<Capacity>::max();
    Graph direct(2);
    direct.add_edge(0, 1, maximum);
    check(direct, 0, 1, maximum);

    Graph dead_end(3);
    dead_end.add_edge(1, 0, maximum);
    check(dead_end, 1, 2, 0); // The sink is unreachable despite a maximum-capacity edge.

    Graph parallel(4);
    parallel.add_edge(2, 0, 4);
    parallel.add_edge(2, 0, 6);
    parallel.add_edge(0, 2, 3);
    parallel.add_edge(0, 1, 7);
    parallel.add_edge(1, 0, 2);
    parallel.add_edge(1, 3, 7);
    parallel.add_edge(3, 2, 8);
    parallel.add_edge(2, 3, 0);
    check(parallel, 2, 3, 7);

    // A cyclic component can send only one unit through the sink bottleneck.
    Graph bottleneck(6);
    bottleneck.add_edge(0, 1, 100);
    bottleneck.add_edge(0, 2, 100);
    bottleneck.add_edge(1, 2, 100);
    bottleneck.add_edge(2, 3, 100);
    bottleneck.add_edge(3, 1, 100);
    bottleneck.add_edge(3, 4, 1);
    bottleneck.add_edge(4, 5, 1);
    check(bottleneck, 0, 5, 1);

    // BFS first chooses 0 -> 1 -> 3 -> 5. Reaching flow 2 then requires
    // 0 -> 2 -> 3 -> 1 -> 4 -> 5, cancelling flow on 1 -> 3.
    Graph reroute(6);
    reroute.add_edge(0, 1, 1);
    reroute.add_edge(0, 2, 1);
    reroute.add_edge(1, 3, 1);
    reroute.add_edge(1, 4, 1);
    reroute.add_edge(2, 3, 1);
    reroute.add_edge(3, 5, 1);
    reroute.add_edge(4, 5, 1);
    check(reroute, 0, 5, 2);

    Graph chain(256);
    for (Vertex u = 0; u + 1 < chain.vertex_count(); ++u)
        chain.add_edge(u, u + 1, u == 254 ? 0 : 9);
    check(chain, 0, 255, 0);

    Graph valid(2);
    for (const auto terminals : {std::pair<Vertex, Vertex>{0, 0}, {2, 1}, {0, 2}}) {
        bool rejected = false;
        try { edmonds_karp(valid, terminals.first, terminals.second); }
        catch (const std::invalid_argument&) { rejected = true; }
        if (!rejected) throw std::runtime_error("invalid terminals were accepted");
    }
}

void exhaustive_four_vertex_graphs() {
    // All 2^12 simple directed unit-capacity graphs, with every distinct pair
    // of terminals. The expected answer enumerates cuts, never flow paths.
    for (unsigned topology = 0; topology < (1u << 12); ++topology) {
        Graph graph(4);
        unsigned bit = 0;
        for (Vertex u = 0; u < 4; ++u)
            for (Vertex v = 0; v < 4; ++v)
                if (u != v) {
                    if (topology & (1u << bit)) graph.add_edge(u, v, 1);
                    ++bit;
                }
        for (Vertex source = 0; source < 4; ++source) {
            for (Vertex sink = 0; sink < 4; ++sink) {
                if (source == sink) continue;
                Capacity expected = std::numeric_limits<Capacity>::max();
                for (unsigned cut = 0; cut < 16; ++cut) {
                    if (!(cut & (1u << source)) || (cut & (1u << sink))) continue;
                    Capacity capacity = 0;
                    for (const auto& edge : graph.original_edges())
                        if ((cut & (1u << edge.from)) && !(cut & (1u << edge.to)))
                            capacity += edge.capacity;
                    expected = std::min(expected, capacity);
                }
                check(graph, source, sink, expected);
            }
        }
    }
}
}

int main() {
    try {
        boundary_cases();
        exhaustive_four_vertex_graphs();
        std::cout << "Edmonds-Karp boundaries and 49,152 graph/terminal cases passed\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

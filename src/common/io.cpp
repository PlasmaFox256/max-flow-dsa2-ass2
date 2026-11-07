#include "maxflow/io.hpp"
#include <stdexcept>
#include <string>

namespace maxflow {
Instance read_instance(std::istream& input) {
    std::int64_t n, m, source, sink;
    if (!(input >> n >> m >> source >> sink) || n < 2 || m < 0 ||
        source < 0 || sink < 0 || source >= n || sink >= n || source == sink)
        throw std::invalid_argument("invalid instance header");
    Graph graph(static_cast<std::size_t>(n));
    for (std::int64_t i = 0; i < m; ++i) {
        std::int64_t u, v, capacity;
        if (!(input >> u >> v >> capacity) || u < 0 || v < 0)
            throw std::invalid_argument("invalid or missing edge");
        graph.add_edge(static_cast<Vertex>(u), static_cast<Vertex>(v), capacity);
    }
    std::string extra;
    if (input >> extra) throw std::invalid_argument("unexpected trailing data");
    return {std::move(graph), static_cast<Vertex>(source), static_cast<Vertex>(sink)};
}
}
